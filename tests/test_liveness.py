from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repogc.config import Config
from repogc.models import SelfCheckResult
from repogc.reporting import report_payload
from repogc.scanner import scan_repository


PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("fixture",))


def liveness_config() -> Config:
    return Config(
        include_suffixes=(".md",),
        orphan_suffixes=(".md",),
        duplicate_suffixes=(),
        exclude_dirs=(".git",),
        root_files=("SKILL.md",),
        marker_tokens=("TODO",),
        graph_root_globs=("SKILL.md",),
        instruction_globs=("SKILL.md",),
        contract_globs=("SKILL.md",),
        use_git=False,
    )


class LivenessProfileTests(unittest.TestCase):
    def test_contract_consumer_is_observed_while_dynamic_meaning_stays_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "Required delivery artifact: process_log.md\n",
                encoding="utf-8",
            )
            (root / "process_log.md").write_text(
                "TODO confirm execution evidence\n",
                encoding="utf-8",
            )
            result = scan_repository(root, liveness_config(), PASSING_SELF_CHECK)
            payload = report_payload(result)
            profile = next(
                item for item in payload["artifact_liveness"] if item["path"] == "process_log.md"
            )
            self.assertEqual(
                profile["dimensions"]["contract_or_instruction_consumer"]["status"],
                "OBSERVED",
            )
            self.assertEqual(profile["dimensions"]["root_reachability"]["status"], "OBSERVED")
            self.assertEqual(profile["dimensions"]["dynamic_consumers"]["status"], "UNKNOWN")
            self.assertEqual(profile["dimensions"]["runtime_access"]["status"], "UNKNOWN")
            self.assertEqual(profile["dimensions"]["business_meaning"]["status"], "NOT_INFERRED")
            self.assertIn("not a deletion", profile["verdict_boundary"])

    def test_missing_target_profile_distinguishes_reference_from_existence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "Required delivery artifact: [log](missing_log.md)\n",
                encoding="utf-8",
            )
            result = scan_repository(root, liveness_config(), PASSING_SELF_CHECK)
            payload = report_payload(result)
            finding = next(
                item
                for item in payload["findings"]
                if item["category"] == "broken_reference"
            )
            self.assertEqual(finding["review_subjects"], ["SKILL.md", "missing_log.md"])
            profile = next(
                item for item in payload["artifact_liveness"] if item["path"] == "missing_log.md"
            )
            self.assertFalse(profile["exists"])
            self.assertEqual(
                profile["dimensions"]["static_inbound_references"]["status"],
                "OBSERVED",
            )
            self.assertEqual(
                profile["dimensions"]["root_reachability"]["status"],
                "NOT_APPLICABLE",
            )


if __name__ == "__main__":
    unittest.main()
