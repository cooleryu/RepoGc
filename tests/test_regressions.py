from __future__ import annotations

import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from repogc import REPORT_SCHEMA_VERSION
from repogc.baseline import baseline_from_report, compare_baseline
from repogc.config import Config
from repogc.models import SelfCheckResult
from repogc.reporting import report_payload, safe_output_path
from repogc.scanner import (
    compute_inbound,
    extract_references,
    scan_repository,
    stable_id,
)
from repogc.self_check import run_self_check


PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("test fixture",))


def narrow_config(**overrides: object) -> Config:
    values: dict[str, object] = {
        "include_suffixes": (".md", ".jsonl"),
        "orphan_suffixes": (".md",),
        "duplicate_suffixes": (),
        "exclude_dirs": (".git", "docs/gc_reports", "reference/gc_reports"),
        "root_files": (),
        "marker_tokens": ("TODO",),
        "use_git": False,
    }
    values.update(overrides)
    return Config(**values)


class HistoricalRegressionTests(unittest.TestCase):
    def test_c1_negation_does_not_swallow_real_reference(self) -> None:
        references = extract_references(
            "README.md",
            "没有 .gitlab-ci.yml，tools/guarded_push.py 只是门禁包装",
            {"README.md", "tools/guarded_push.py"},
        )
        self.assertEqual([reference.raw for reference in references], ["tools/guarded_push.py"])

    def test_c2_mutually_referenced_documents_are_not_orphans(self) -> None:
        known = {"core_principles_memo.md", "provenance_seal_mechanism.md"}
        references = extract_references(
            "core_principles_memo.md",
            "See provenance_seal_mechanism.md",
            known,
        ) + extract_references(
            "provenance_seal_mechanism.md",
            "See core_principles_memo.md",
            known,
        )
        inbound = compute_inbound(references, known)
        self.assertEqual(inbound["core_principles_memo.md"], {"provenance_seal_mechanism.md"})
        self.assertEqual(inbound["provenance_seal_mechanism.md"], {"core_principles_memo.md"})

    def test_c3_inserting_an_earlier_line_does_not_change_finding_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            skill.write_text("# Contract\nTODO preserve this contract\n", encoding="utf-8")
            config = narrow_config(root_files=("SKILL.md",))
            before = scan_repository(root, config, PASSING_SELF_CHECK)
            before_id = next(
                finding.id
                for finding in before.findings
                if finding.category == "unimplemented_marker"
            )
            skill.write_text(
                "Inserted context\n# Contract\nTODO preserve this contract\n",
                encoding="utf-8",
            )
            after = scan_repository(root, config, PASSING_SELF_CHECK)
            after_id = next(
                finding.id
                for finding in after.findings
                if finding.category == "unimplemented_marker"
            )
            self.assertEqual(before_id, after_id)

    def test_c4_jsonl_suffix_is_not_truncated(self) -> None:
        references = extract_references("README.md", "Read example.jsonl", {"README.md"})
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0].raw, "example.jsonl")
        self.assertEqual(references[0].target, "example.jsonl")

    def test_c5_scanner_hash_change_marks_trend_basis_changed(self) -> None:
        trend = compare_baseline(
            [],
            {
                "scanner_hash": "old",
                "config_hash": "same",
                "report_schema_version": REPORT_SCHEMA_VERSION,
                "findings": [],
            },
            scanner_hash="new",
            config_hash="same",
            report_schema=REPORT_SCHEMA_VERSION,
        )
        self.assertTrue(trend["basis_changed"])
        self.assertIn("scanner_hash changed", trend["basis_change_reasons"])

    def test_c6_skill_contract_is_an_inbound_consumer(self) -> None:
        known = {"SKILL.md", "process_log.md"}
        references = extract_references(
            "SKILL.md",
            "Required delivery artifact: process_log.md",
            known,
        )
        inbound = compute_inbound(references, known)
        self.assertEqual(inbound["process_log.md"], {"SKILL.md"})


class SafetyAndDeterminismTests(unittest.TestCase):
    def test_python_build_metadata_is_excluded_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            metadata = root / "src" / "demo.egg-info"
            metadata.mkdir(parents=True)
            (metadata / "SOURCES.txt").write_text(
                "README.md\nsrc/demo.py\n",
                encoding="utf-8",
            )
            result = scan_repository(root, Config(use_git=False), PASSING_SELF_CHECK)
            self.assertEqual(result.scanned_files, 1)
            self.assertFalse(
                any(".egg-info" in artifact.path for artifact in result.artifacts)
            )

    def test_impossible_duplicate_pair_skips_expensive_similarity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("a" * 1000, encoding="utf-8")
            (root / "legacy.md").write_text("a" * 200, encoding="utf-8")
            config = narrow_config(
                duplicate_suffixes=(".md",),
                duplicate_min_chars=120,
                duplicate_threshold=0.96,
            )
            with mock.patch(
                "repogc.scanner.difflib.SequenceMatcher",
                side_effect=AssertionError("mathematically impossible pair was compared"),
            ):
                result = scan_repository(root, config, PASSING_SELF_CHECK)
            self.assertFalse(
                any(finding.category == "duplicate_candidate" for finding in result.findings)
            )

    def test_sentinel_covers_all_historical_cases(self) -> None:
        result = run_self_check()
        self.assertTrue(result.ok, result.failures)
        self.assertEqual(len(result.checks), 17)

    def test_scan_is_report_only_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("See docs/live.md\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "live.md").write_text("TODO document behavior\n", encoding="utf-8")
            config = narrow_config(root_files=("README.md",))
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            first = scan_repository(root, config, PASSING_SELF_CHECK)
            second = scan_repository(root, config, PASSING_SELF_CHECK)
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertEqual(
                [finding.to_dict() for finding in first.findings],
                [finding.to_dict() for finding in second.findings],
            )
            self.assertEqual(first.reliability, "RELIABLE")

    def test_self_reference_does_not_count_as_inbound(self) -> None:
        known = {"notes.md"}
        references = extract_references("notes.md", "See notes.md", known)
        inbound = compute_inbound(references, known)
        self.assertEqual(inbound["notes.md"], set())

    def test_failed_sentinel_marks_scan_unreliable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("ok\n", encoding="utf-8")
            failed = SelfCheckResult(ok=False, checks=(), failures=("fixture failed",))
            result = scan_repository(
                root,
                narrow_config(root_files=("README.md",)),
                failed,
            )
            self.assertEqual(result.reliability, "UNRELIABLE")
            self.assertIn("fixture failed", result.reliability_reasons)

    def test_non_reliable_report_cannot_become_baseline(self) -> None:
        with self.assertRaisesRegex(ValueError, "RELIABLE"):
            baseline_from_report(
                {
                    "metadata": {"reliability": "PARTIAL"},
                    "findings": [],
                }
            )

    def test_output_path_cannot_escape_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "escapes"):
                safe_output_path(root, "../outside.json")

    def test_report_does_not_include_absolute_repository_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("TODO test\n", encoding="utf-8")
            result = scan_repository(
                root,
                narrow_config(root_files=("README.md",)),
                PASSING_SELF_CHECK,
            )
            payload = report_payload(result)
            self.assertNotIn(str(root), str(payload))

    def test_git_last_touch_does_not_expose_author_field(self) -> None:
        from repogc.git_info import last_touch

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("private fixture\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "-c",
                    "user.name=Private Author",
                    "-c",
                    "user.email=private@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "fixture",
                ],
                check=True,
            )
            context = last_touch(root, "README.md", enabled=True)
            self.assertIsNotNone(context)
            self.assertEqual(set(context or {}), {"date", "commit"})
            self.assertNotIn("Private Author", str(context))
            self.assertNotIn("private@example.invalid", str(context))

    def test_repository_info_reports_dirty_as_boolean_without_paths(self) -> None:
        from repogc.git_info import repository_info

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "private-name.md").write_text("fixture\n", encoding="utf-8")
            repository, problem = repository_info(root, enabled=True)
            self.assertTrue(repository["dirty"])
            self.assertNotIn("private-name.md", str(repository))
            self.assertIn("no commit yet", problem or "")

    def test_existing_target_in_excluded_directory_is_not_broken(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text(
                "See reports/generated.json\n",
                encoding="utf-8",
            )
            (root / "reports").mkdir()
            (root / "reports" / "generated.json").write_text("{}\n", encoding="utf-8")
            result = scan_repository(
                root,
                narrow_config(
                    include_suffixes=(".md", ".json"),
                    root_files=("README.md",),
                    exclude_dirs=(".git", "reports"),
                ),
                PASSING_SELF_CHECK,
            )
            broken = [
                finding
                for finding in result.findings
                if finding.category == "broken_reference"
            ]
            self.assertEqual(broken, [])

    def test_markdown_link_label_is_not_a_second_path_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text(
                "See [`phase0-bootstrap.md`](reports/phase0-bootstrap.md)\n",
                encoding="utf-8",
            )
            (root / "reports").mkdir()
            (root / "reports" / "phase0-bootstrap.md").write_text("report\n", encoding="utf-8")
            result = scan_repository(
                root,
                narrow_config(
                    root_files=("README.md",),
                    exclude_dirs=(".git", "reports"),
                ),
                PASSING_SELF_CHECK,
            )
            broken = [
                finding
                for finding in result.findings
                if finding.category == "broken_reference"
            ]
            self.assertEqual(broken, [])


if __name__ == "__main__":
    unittest.main()
