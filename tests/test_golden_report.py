from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from repogc.config import Config, LivenessDeclaration
from repogc.models import SelfCheckResult
from repogc.reporting import report_payload
from repogc.scanner import scan_repository


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "golden-report"
EXPECTED = ROOT / "tests" / "golden" / "minimal-report.json"
PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("golden fixture",))


def canonical_report() -> dict[str, Any]:
    config = Config(
        include_suffixes=(".md",),
        orphan_suffixes=(".md",),
        duplicate_suffixes=(),
        exclude_dirs=(".git",),
        exclude_globs=(),
        root_files=("README.md",),
        marker_tokens=("TODO",),
        graph_root_globs=("README.md",),
        instruction_globs=("SKILL.md",),
        contract_globs=("SKILL.md",),
        test_globs=(),
        generated_globs=(),
        liveness_declarations=(
            LivenessDeclaration(
                path="process_log.md",
                kind="dynamic_consumer",
                source="golden registry",
                reason="Loaded through a computed case path.",
            ),
        ),
        use_git=False,
    )
    payload = report_payload(scan_repository(FIXTURE, config, PASSING_SELF_CHECK))
    return {
        "report_schema_version": payload["metadata"]["report_schema_version"],
        "reliability": payload["metadata"]["reliability"],
        "scan_integrity": payload["metadata"]["scan_integrity"],
        "summary": payload["summary"],
        "findings": [
            {
                key: finding[key]
                for key in (
                    "id",
                    "category",
                    "source",
                    "target",
                    "evidence",
                    "rule",
                    "evidence_kind",
                    "evidence_strength",
                    "contract_sensitive",
                    "review_subjects",
                )
            }
            for finding in payload["findings"]
        ],
        "artifact_liveness": [
            {
                "path": profile["path"],
                "exists": profile["exists"],
                "incoming_edge_counts": profile["incoming_edge_counts"],
                "dimension_statuses": {
                    name: dimension["status"]
                    for name, dimension in profile["dimensions"].items()
                },
            }
            for profile in payload["artifact_liveness"]
        ],
        "artifacts": [
            {
                key: artifact[key]
                for key in (
                    "path",
                    "role",
                    "exists",
                    "root",
                    "reachable",
                    "reachable_from",
                    "evidence_path",
                    "incoming_edge_kinds",
                )
            }
            for artifact in payload["artifacts"]
        ],
        "edges": [
            {
                key: edge[key]
                for key in (
                    "id",
                    "source",
                    "target",
                    "kind",
                    "syntax",
                    "strength",
                    "traversable",
                    "contract_sensitive",
                )
            }
            for edge in payload["edges"]
        ],
    }


class GoldenReportTests(unittest.TestCase):
    def test_minimal_report_contract_matches_golden_file(self) -> None:
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(canonical_report(), expected)


if __name__ == "__main__":
    unittest.main()
