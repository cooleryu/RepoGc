from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from repogc.annotations import (
    ANNOTATION_SCHEMA_VERSION,
    validate_annotation_input,
    validate_annotation_sidecar,
)
from repogc.cli import main
from repogc.config import Config
from repogc.models import SelfCheckResult
from repogc.reporting import report_payload
from repogc.scanner import scan_repository


PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("fixture",))


def mechanical_report(root: Path) -> dict[str, object]:
    (root / "README.md").write_text("TODO confirm contract\n", encoding="utf-8")
    result = scan_repository(
        root,
        Config(
            include_suffixes=(".md",),
            orphan_suffixes=(".md",),
            duplicate_suffixes=(),
            root_files=("README.md",),
            graph_root_globs=("README.md",),
            marker_tokens=("TODO",),
            use_git=False,
        ),
        PASSING_SELF_CHECK,
    )
    return report_payload(result)


def valid_input(finding_id: str) -> dict[str, object]:
    return {
        "provider": "fixture-provider",
        "model": "fixture-model",
        "data_handling": "Fixture content stayed in the local test process.",
        "annotations": [
            {
                "finding_id": finding_id,
                "observed_background": "Current evidence shows this text in the repository root.",
                "evidence_sources": ["README.md"],
                "uncertainties": ["The current business intent is unknown."],
                "human_checks": ["Confirm whether the commitment is still active."],
            }
        ],
    }


class AnnotationBoundaryTests(unittest.TestCase):
    def test_valid_sidecar_binds_to_report_without_mutating_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = mechanical_report(Path(temporary))
            before = copy.deepcopy(report)
            finding_id = str(report["findings"][0]["id"])
            sidecar = validate_annotation_input(report, valid_input(finding_id))
            self.assertEqual(report, before)
            self.assertEqual(sidecar["annotation_schema_version"], ANNOTATION_SCHEMA_VERSION)
            self.assertEqual(sidecar["annotations"][0]["finding_id"], finding_id)
            expected_hash = hashlib.sha256(
                json.dumps(
                    report,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            self.assertEqual(
                sidecar["mechanical_report"]["canonical_report_sha256"],
                expected_hash,
            )
            self.assertTrue(sidecar["annotations"][0]["ai_generated"])
            self.assertFalse(sidecar["annotations"][0]["human_verified"])
            self.assertFalse(sidecar["mechanical_report_modified"])
            self.assertEqual(validate_annotation_sidecar(report, sidecar), sidecar)

            tampered = copy.deepcopy(sidecar)
            tampered["mechanical_report"]["canonical_report_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                validate_annotation_sidecar(report, tampered)

    def test_verdict_language_is_rejected_in_english_and_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = mechanical_report(Path(temporary))
            finding_id = str(report["findings"][0]["id"])
            for verdict in (
                "This file is safe to delete.",
                "Keep this file.",
                "这个文件可以删除。",
                "这个文件应当保留。",
            ):
                with self.subTest(verdict=verdict):
                    annotation_input = valid_input(finding_id)
                    annotation_input["annotations"][0]["observed_background"] = verdict
                    with self.assertRaises(ValueError):
                        validate_annotation_input(report, annotation_input)

    def test_unknown_finding_source_and_reserved_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = mechanical_report(Path(temporary))
            finding_id = str(report["findings"][0]["id"])
            cases = []
            unknown_finding = valid_input("missing-id")
            cases.append(unknown_finding)
            unknown_source = valid_input(finding_id)
            unknown_source["annotations"][0]["evidence_sources"] = ["outside.md"]
            cases.append(unknown_source)
            reserved_field = valid_input(finding_id)
            reserved_field["annotations"][0]["severity"] = "low"
            cases.append(reserved_field)
            reserved_top_level = valid_input(finding_id)
            reserved_top_level["verdict"] = "keep"
            cases.append(reserved_top_level)
            for annotation_input in cases:
                with self.subTest(annotation_input=annotation_input):
                    with self.assertRaises(ValueError):
                        validate_annotation_input(report, annotation_input)

    def test_unreliable_report_cannot_be_annotated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = mechanical_report(Path(temporary))
            report["metadata"]["reliability"] = "UNRELIABLE"
            finding_id = str(report["findings"][0]["id"])
            with self.assertRaises(ValueError):
                validate_annotation_input(report, valid_input(finding_id))

    def test_incompatible_schema_and_duplicate_report_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = mechanical_report(Path(temporary))
            finding_id = str(report["findings"][0]["id"])
            report["metadata"]["report_schema_version"] = "0.5"
            with self.assertRaises(ValueError):
                validate_annotation_input(report, valid_input(finding_id))

            report = mechanical_report(Path(temporary))
            report["findings"].append(copy.deepcopy(report["findings"][0]))
            with self.assertRaises(ValueError):
                validate_annotation_input(report, valid_input(finding_id))

    def test_cli_skips_without_provider_and_writes_separate_validated_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "repogc.toml"
            config.write_text(
                """
[scan]
include_suffixes = [".md"]
orphan_suffixes = [".md"]
duplicate_suffixes = []
exclude_dirs = ["reports", "reference"]
root_files = ["README.md"]
use_git = false

[markers]
tokens = ["TODO"]

[graph]
root_globs = ["README.md"]

[reports]
markdown = "reports/latest.md"
json = "reports/latest.json"
baseline = "reference/baseline.json"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("TODO confirm contract\n", encoding="utf-8")

            skipped_stdout = io.StringIO()
            with contextlib.redirect_stdout(skipped_stdout):
                self.assertEqual(main(["annotate", "--root", str(root)]), 0)
            self.assertIn("annotation skipped", skipped_stdout.getvalue())
            self.assertFalse((root / "reports").exists())

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["scan", str(root)]), 0)
            report_path = root / "reports" / "latest.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            finding_id = str(report["findings"][0]["id"])
            input_path = root / "annotation-input.json"
            input_path.write_text(
                json.dumps(valid_input(finding_id), ensure_ascii=False),
                encoding="utf-8",
            )
            before = report_path.read_bytes()
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "annotate",
                        "--root",
                        str(root),
                        "--input",
                        "annotation-input.json",
                        "--output",
                        "reports/annotations.json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(report_path.read_bytes(), before)
            sidecar = json.loads(
                (root / "reports" / "annotations.json").read_text(encoding="utf-8")
            )
            self.assertFalse(sidecar["mechanical_report_modified"])
            self.assertIn("Mechanical report modified: false", stdout.getvalue())

    def test_cli_rejects_oversized_annotation_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            oversized = root / "oversized.json"
            oversized.write_text(" " * 1_000_001, encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(
                    [
                        "annotate",
                        "--root",
                        str(root),
                        "--input",
                        str(oversized),
                    ]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("exceeds 1000000 bytes", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
