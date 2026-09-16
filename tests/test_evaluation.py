from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.run import (DIMENSIONS, check_expectation, digest_json, run_suite,
                       validate_ai_review, validate_suite)
from repogc.models import SelfCheckResult
from repogc.scanner import scan_repository


PROJECT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.run_dir = Path(cls.temporary.name) / "run"
        cls.summary = run_suite(PROJECT / "evals/cases.json", cls.run_dir)
        cls.packet = json.loads((cls.run_dir / "ai-review-packet.json").read_text())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def review_record(self) -> dict:
        # Synthetic validator input, not an actual model review.
        return {"schema_version": "1", "packet_sha256": digest_json(self.packet),
                "reviewer": {key: "synthetic unit test; no model ran" for key in
                             ("agent", "model", "independence", "exposure", "execution")},
                "cases": [{"id": case["id"], "dimensions": {
                    name: {"rating": "not_assessed", "reason": "Validator fixture only",
                           "citations": []} for name in DIMENSIONS}}
                          for case in self.packet["cases"]]}

    def test_development_expectations_and_invariants(self) -> None:
        failures = [item for item in self.summary["results"] if item["status"] != "passed"]
        self.assertEqual(failures, [])
        self.assertEqual(self.summary["engineering"]["passed"], len(self.packet["cases"]))

    def test_unrun_layers_never_become_passed(self) -> None:
        self.assertEqual(self.summary["ai_review"]["status"], "not_run")
        self.assertEqual(self.summary["human_outcome"]["status"], "not_run")
        self.assertEqual(self.summary["release_readiness"], "not_established")
        self.assertTrue(all(item["human_decision_count"] is None for item in self.summary["results"]))

    def test_original_bundle_and_existing_output_are_preserved(self) -> None:
        before = (self.run_dir / "summary.json").read_bytes()
        with self.assertRaises(FileExistsError):
            run_suite(PROJECT / "evals/cases.json", self.run_dir)
        self.assertEqual(before, (self.run_dir / "summary.json").read_bytes())

    def test_late_output_failure_never_publishes_success_summary(self) -> None:
        original_write = Path.write_text
        def fail_markdown(path, data, *args, **kwargs):
            if path.name == "summary.md":
                raise OSError("simulated late output failure")
            return original_write(path, data, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            with patch.object(Path, "write_text", fail_markdown):
                with self.assertRaisesRegex(OSError, "late output failure"):
                    run_suite(PROJECT / "evals/cases.json", output)
            self.assertFalse((output / "summary.json").exists())
            failure = json.loads((output / "failure.json").read_text())
            self.assertEqual(failure["status"], "incomplete")

    def test_partial_ai_record_is_not_quality_pass(self) -> None:
        result = validate_ai_review(self.review_record(), self.run_dir)
        self.assertTrue(result["record_valid"])
        self.assertEqual(result["assessment_coverage"], "partial")
        self.assertFalse(result["judgments_verified"])
        self.assertEqual(result["release_readiness"], "not_established")

    def test_wrong_packet_missing_case_and_rubric_are_rejected(self) -> None:
        for mutation in (lambda r: r.update(packet_sha256="wrong"),
                         lambda r: r["cases"].pop(),
                         lambda r: r["cases"][0]["dimensions"].pop(DIMENSIONS[0])):
            review = self.review_record()
            mutation(review)
            with self.assertRaises(ValueError):
                validate_ai_review(review, self.run_dir)

    def test_assessments_need_verifiable_case_specific_quotes(self) -> None:
        review = self.review_record()
        case = review["cases"][0]
        assessment = case["dimensions"][DIMENSIONS[0]]
        assessment["rating"] = "adequate"
        with self.assertRaises(ValueError):
            validate_ai_review(review, self.run_dir)
        evidence = case["id"] + "/review.json"
        first_line = (self.run_dir / evidence).read_text().splitlines()[0]
        citation = {"path": evidence, "line_start": 1, "line_end": 1, "quote": first_line}
        assessment["citations"] = [citation]
        self.assertTrue(validate_ai_review(review, self.run_dir)["record_valid"])
        # Syntactically valid braces are not meaningful support: no truth claim.
        self.assertFalse(validate_ai_review(review, self.run_dir)["judgments_verified"])
        for key, value in (("quote", "fabricated evidence"), ("line_end", 999999),
                           ("path", "../secret"), ("line_start", True)):
            bad = copy.deepcopy(review)
            bad["cases"][0]["dimensions"][DIMENSIONS[0]]["citations"][0][key] = value
            with self.assertRaises(ValueError):
                validate_ai_review(bad, self.run_dir)

    def test_changed_sources_invalidate_review(self) -> None:
        path = self.run_dir / self.packet["cases"][0]["review"]
        original = path.read_bytes()
        try:
            path.write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "Evidence changed"):
                validate_ai_review(self.review_record(), self.run_dir)
        finally:
            path.write_bytes(original)

    def test_added_source_or_symlink_invalidates_review(self) -> None:
        path = self.run_dir / self.packet["cases"][0]["source_dir"] / "new-consumer.py"
        try:
            path.write_text("# New counterevidence\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inventory changed"):
                validate_ai_review(self.review_record(), self.run_dir)
            path.unlink()
            path.symlink_to(self.run_dir / "summary.json")
            with self.assertRaises(ValueError):
                validate_ai_review(self.review_record(), self.run_dir)
        finally:
            path.unlink(missing_ok=True)

    def test_scanner_mutation_is_detected_by_evaluator(self) -> None:
        def mutating_scan(root, config, checks):
            result = scan_repository(root, config, checks)
            (root / "injected.txt").write_text("accidental target write", encoding="utf-8")
            return result
        with tempfile.TemporaryDirectory() as temporary:
            with patch("evals.run.scan_repository", side_effect=mutating_scan):
                result = run_suite(PROJECT / "evals/cases.json", Path(temporary) / "run")
            self.assertEqual(result["engineering"]["status"], "failed")
            self.assertTrue(all(not item["invariants"]["source_bytes_unchanged"]
                                for item in result["results"]))

    def test_synthetic_path_escape_duplicate_ids_and_holdout_claim_rejected(self) -> None:
        suite = json.loads((PROJECT / "evals/cases.json").read_text())
        for path in ("../escape.md", "/absolute.md", "a/../../escape.md", "a\\escape.md"):
            bad = copy.deepcopy(suite)
            bad["cases"][0]["files"] = {path: "untrusted"}
            with self.assertRaises(ValueError):
                validate_suite(bad)
        bad = copy.deepcopy(suite)
        bad["cases"].append(bad["cases"][0])
        with self.assertRaises(ValueError):
            validate_suite(bad)
        suite["split"] = "held_out"
        with self.assertRaises(ValueError):
            validate_suite(suite)

    def test_fixture_git_metadata_and_git_execution_are_rejected(self) -> None:
        suite = json.loads((PROJECT / "evals/cases.json").read_text())
        for path in (".git/config", "nested/.git/config", ".GIT/config"):
            bad = copy.deepcopy(suite)
            bad["cases"][0]["files"][path] = "untrusted Git configuration"
            with self.assertRaises(ValueError):
                validate_suite(bad)
        suite["cases"][0]["config"] = "[scan]\nuse_git = true\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "suite.json"
            path.write_text(json.dumps(suite), encoding="utf-8")
            with patch("evals.run.scan_repository") as scanner:
                with self.assertRaisesRegex(ValueError, "use_git=false"):
                    run_suite(path, Path(temporary) / "run")
                scanner.assert_not_called()
            failure = json.loads((Path(temporary) / "run/failure.json").read_text())
            self.assertEqual(failure["status"], "incomplete")
            self.assertFalse((Path(temporary) / "run/summary.json").exists())

    def test_unknown_or_false_expectation_cannot_silently_pass(self) -> None:
        with self.assertRaises(ValueError):
            check_expectation({"kind": "imaginary"}, {}, {})
        self.assertFalse(check_expectation({"kind": "finding_present", "source": "x.md",
                                           "category": "broken_reference"},
                                          {"findings": []}, {}))

    def test_absence_oracles_cannot_pass_with_typo_or_nonexistent_source(self) -> None:
        suite = json.loads((PROJECT / "evals/cases.json").read_text())
        for spec in (
            {"kind": "finding_absent", "source": "not-authored.md", "category": "broken_reference"},
            {"kind": "finding_absent", "source": "README.md", "category": "misspelled_category"},
            {"kind": "review_max_cards", "value": True},
            {"kind": "unknown_expectation"},
        ):
            suite["cases"][0]["expectations"] = [spec]
            with self.assertRaises(ValueError):
                validate_suite(suite)

    def test_empty_duplicate_or_wrong_split_packet_is_rejected(self) -> None:
        path = self.run_dir / "ai-review-packet.json"
        original = path.read_bytes()
        try:
            for mutation in (lambda p: p.update(cases=[]),
                             lambda p: p.update(split="held_out"),
                             lambda p: p["cases"].append(p["cases"][0]),
                             lambda p: p["cases"][0].update(source_dir="../outside"),
                             lambda p: p["files"].pop(p["cases"][0]["report"])):
                packet = copy.deepcopy(self.packet)
                mutation(packet)
                path.write_text(json.dumps(packet), encoding="utf-8")
                record = self.review_record()
                record["packet_sha256"] = digest_json(packet)
                with self.assertRaises(ValueError):
                    validate_ai_review(record, self.run_dir)
        finally:
            path.write_bytes(original)

    def test_failed_sentinels_fail_engineering_and_refuse_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch("evals.run.run_self_check", return_value=SelfCheckResult(
                    ok=False, checks=(), failures=("injected test failure",))):
                result = run_suite(PROJECT / "evals/cases.json", Path(temporary) / "run")
            self.assertEqual(result["engineering"]["status"], "failed")
            self.assertTrue(all(item["counts"]["cards"] == 0 for item in result["results"]))


if __name__ == "__main__":
    unittest.main()
