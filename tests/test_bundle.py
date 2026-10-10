from __future__ import annotations

import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from repogc.bundle import build_bundle, canonical_digest, validate_bundle, write_bundle, verify_bundle
from repogc.config import Config
from repogc.cli import main
from repogc.reporting import report_payload
from repogc.review import build_review_payload
from repogc.scanner import scan_repository
from repogc.self_check import run_self_check
from unittest.mock import patch


class BundleTests(unittest.TestCase):
    def fixture(self, root):
        case = next(c for c in json.loads((Path(__file__).parents[1] / "evals/cases.json").read_text())["cases"]
                    if c["id"] == "many-independent-broken-references")
        for name, text in case["files"].items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        config = Config(use_git=False, duplicate_suffixes=())
        result = scan_repository(root, config, run_self_check())
        report = report_payload(result)
        return config, result, report, build_review_payload(report)

    def test_all_seven_findings_survive_single_card_and_source_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            config, result, report, review = self.fixture(root)
            bundle = build_bundle(result, report, config, review)
            self.assertEqual(len(bundle["payload"]["selection_ledger"]), 7)
            ledger = bundle["payload"]["selection_ledger"]
            # Broken links are certain, so every one is listed rather than sampled into a card.
            self.assertTrue(all(x["reason"] == "listed_as_problem" for x in ledger))
            output = Path(temporary) / "bundle"
            write_bundle(root, output, bundle)
            before = (output / "bundle.json").read_bytes()
            (root / "docs/billing.md").write_text("changed later", encoding="utf-8")
            checked = verify_bundle(output, bundle["sha256"])
            self.assertEqual(checked["finding_count"], 7)
            self.assertFalse(checked["live_source_freshness_verified"])
            self.assertEqual(before, (output / "bundle.json").read_bytes())

    def test_tampering_missing_sources_and_incomplete_ledgers_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, result, report, review = self.fixture(Path(temporary))
            original = build_bundle(result, report, config, review)
            for mutation in (
                lambda p: p["sources"].pop("docs/billing.md"),
                lambda p: p["selection_ledger"].pop(),
                lambda p: p["selection_ledger"].append(p["selection_ledger"][0]),
                lambda p: p.update(actions=["unauthorized"]),
                lambda p: p["configuration"].update(use_git=True),
                lambda p: p["sources"].update({"../escape": "text"}),
                lambda p: p["review"]["problems"][0].update(source="unrelated.md"),
                lambda p: p["review"]["problems"].append(p["review"]["problems"][0]),
                lambda p: p["review"]["safety"].update(action_verdict=True),
            ):
                bad = copy.deepcopy(original)
                mutation(bad["payload"])
                bad["sha256"] = canonical_digest(bad["payload"])
                with self.assertRaises(ValueError):
                    validate_bundle(bad)
            bad = copy.deepcopy(original)
            bad["payload"]["sources"]["README.md"] += "changed"
            with self.assertRaises(ValueError):
                validate_bundle(bad)
            with self.assertRaises(ValueError):
                validate_bundle(original, "wrong external digest")

    def test_cli_bundle_and_verification_preserve_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            self.fixture(root)
            (root / "repogc.toml").write_text("[scan]\nuse_git = false\n")
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            output = Path(temporary) / "bundle"
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["review", str(root), "--bundle", str(output), "--json"]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["raw_signal_count"], 7)
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["verify-bundle", str(output)]), 0)
                self.assertEqual(main(["verify-bundle", str(output), "--expected-sha256", "wrong"]), 2)
                self.assertEqual(main(["review", str(root), "--bundle", str(output)]), 2)
                self.assertEqual(main(["review", str(root), "--bundle", str(output), "--report", "old.json"]), 2)

    def test_version_duplicate_keys_size_and_late_failure_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            config, result, report, review = self.fixture(root)
            bundle = build_bundle(result, report, config, review)
            bad = copy.deepcopy(bundle)
            bad["bundle_schema_version"] = "unknown"
            with self.assertRaises(ValueError):
                validate_bundle(bad)
            output = Path(temporary) / "bundle"
            with patch("repogc.bundle.MAX_BUNDLE_BYTES", 10):
                with self.assertRaises(ValueError):
                    write_bundle(root, output, bundle)
            self.assertFalse(output.exists())
            with patch.object(Path, "rename", side_effect=OSError("publication failed")):
                with self.assertRaises(OSError):
                    write_bundle(root, output, bundle)
            with self.assertRaises(ValueError):
                verify_bundle(output)
            (output / "bundle.json").write_text('{"sha256":"one","sha256":"two"}')
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                verify_bundle(output)

    def test_output_does_not_overwrite_or_enter_target_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            args = self.fixture(root)
            bundle = build_bundle(args[1], args[2], args[0], args[3])
            with self.assertRaises(ValueError):
                write_bundle(root, root / "bundle", bundle)
            output = Path(temporary) / "bundle"
            write_bundle(root, output, bundle)
            with self.assertRaises(FileExistsError):
                write_bundle(root, output, bundle)
            alias = Path(temporary) / "alias"
            alias.symlink_to(output, target_is_directory=True)
            with self.assertRaises(ValueError):
                verify_bundle(alias)
            (output / "bundle.json").unlink()
            with self.assertRaises(ValueError):
                verify_bundle(output)

    def test_partial_coverage_is_kept_and_unreliable_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("x" * 100)
            config = Config(use_git=False, max_file_bytes=10)
            result = scan_repository(root, config, run_self_check())
            report = report_payload(result)
            bundle = build_bundle(result, report, config, build_review_payload(report))
            self.assertEqual(validate_bundle(bundle)["reliability"], "PARTIAL")
            self.assertEqual(bundle["payload"]["unscanned"][0]["path"], "README.md")
            report["metadata"]["reliability"] = "UNRELIABLE"
            with self.assertRaises(ValueError):
                build_bundle(result, report, config, {})
