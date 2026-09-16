from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from repogc.cli import main


CONFIG = """
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


class ReviewProductTests(unittest.TestCase):
    def _project(self, root: Path) -> None:
        (root / "README.md").write_text(
            "[Plan](plan.md)\nExample: docs/missing.md\n",
            encoding="utf-8",
        )
        (root / "plan.md").write_text(
            "- [ ] TODO connect the workflow.\n",
            encoding="utf-8",
        )
        (root / "notes.md").write_text("Standalone review notes.\n", encoding="utf-8")
        (root / "repogc.toml").write_text(CONFIG + "\n", encoding="utf-8")

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_review_is_short_plain_and_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root)
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            exit_code, output, error = self._run(
                ["review", str(root), "--limit", "3"]
            )
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(exit_code, 0)
            self.assertEqual(error, "")
            self.assertEqual(before, after)
            self.assertIn("RepoGC review", output)
            self.assertIn("items from", output)
            self.assertIn("no files changed", output)
            self.assertIn("Context:", output)
            self.assertIn("Limits:", output)
            self.assertIn("Check:", output)
            self.assertNotIn("report_schema_version", output)
            self.assertNotIn("finding_ids", output)

    def test_review_shows_one_representative_per_concern_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root)
            exit_code, output, error = self._run(
                ["review", str(root), "--json"]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(error, "")
            payload = json.loads(output)
            concern_kinds = [card["concern_kind"] for card in payload["cards"]]
            self.assertEqual(len(concern_kinds), len(set(concern_kinds)))
            self.assertNotIn(
                "repogc.toml", {card["subject"] for card in payload["cards"]}
            )

    def test_review_json_is_bounded_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root)
            first = self._run(["review", str(root), "--limit", "2", "--json"])
            second = self._run(["review", str(root), "--limit", "2", "--json"])
            self.assertEqual(first, second)
            payload = json.loads(first[1])
            self.assertEqual(payload["shown_count"], 2)
            self.assertGreater(payload["raw_signal_count"], payload["shown_count"])
            self.assertLessEqual(
                payload["review_signal_count"], payload["raw_signal_count"]
            )
            self.assertFalse(payload["safety"]["files_changed"])
            self.assertFalse(payload["safety"]["action_verdict"])
            self.assertTrue(all(card["human_checks"] for card in payload["cards"]))

    def test_review_can_render_a_validated_ai_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root)
            self.assertEqual(self._run(["scan", str(root)])[0], 0)
            report = json.loads(
                (root / "reports" / "latest.json").read_text(encoding="utf-8")
            )
            finding = next(
                item
                for item in report["findings"]
                if item["source"] == "plan.md"
            )
            annotation_input = {
                "provider": "openai-codex-interactive",
                "model": "codex-session-model-unspecified",
                "data_handling": "Selected fixture evidence was processed in the active Codex session.",
                "annotations": [
                    {
                        "finding_id": finding["id"],
                        "observed_background": "The source presents this text as a current workflow status.",
                        "evidence_sources": ["plan.md"],
                        "uncertainties": ["Later implementation evidence has not been inspected."],
                        "human_checks": ["Compare the statement with the newest workflow test."],
                    }
                ],
            }
            (root / "input.json").write_text(
                json.dumps(annotation_input),
                encoding="utf-8",
            )
            self.assertEqual(
                self._run(
                    [
                        "annotate",
                        "--root",
                        str(root),
                        "--input",
                        "input.json",
                        "--output",
                        "reports/sidecar.json",
                    ]
                )[0],
                0,
            )
            exit_code, output, error = self._run(
                [
                    "review",
                    str(root),
                    "--report",
                    "reports/latest.json",
                    "--annotations",
                    "reports/sidecar.json",
                    "--json",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(error, "")
            payload = json.loads(output)
            card = next(item for item in payload["cards"] if item["subject"] == "plan.md")
            self.assertTrue(card["ai_context_used"])
            self.assertIn(annotation_input["annotations"][0]["observed_background"], card["context"])

    def test_review_rejects_an_unbounded_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root)
            exit_code, _, error = self._run(
                ["review", str(root), "--limit", "6"]
            )
            self.assertEqual(exit_code, 2)
            self.assertIn("between 1 and 5", error)


if __name__ == "__main__":
    unittest.main()
