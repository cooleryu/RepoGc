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
max_file_bytes = 100000
duplicate_threshold = 0.96
duplicate_min_chars = 120
use_git = false

[markers]
tokens = ["TODO", "FIXME"]

[graph]
root_globs = ["README.md"]

[reports]
markdown = "reports/latest.md"
json = "reports/latest.json"
baseline = "reference/baseline.json"
""".strip()


class ReviewCliTests(unittest.TestCase):
    def _project(self, root: Path) -> None:
        (root / "README.md").write_text("[Plan](plan.md)\n", encoding="utf-8")
        (root / "plan.md").write_text("TODO active commitment\n", encoding="utf-8")
        (root / "repogc.toml").write_text(CONFIG + "\n", encoding="utf-8")

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_explain_renders_evidence_unknowns_and_structured_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root)
            self.assertEqual(self._run(["scan", str(root)])[0], 0)
            report = json.loads((root / "reports" / "latest.json").read_text(encoding="utf-8"))
            finding = next(
                item for item in report["findings"] if item["category"] == "unimplemented_marker"
            )

            exit_code, output, error = self._run(
                ["explain", finding["id"], "--root", str(root)]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(error, "")
            self.assertIn("Artifact liveness evidence", output)
            self.assertIn("dynamic_consumers: UNKNOWN", output)
            self.assertIn("does not decide whether", output)

            exit_code, output, _ = self._run(
                ["explain", finding["id"], "--root", str(root), "--json"]
            )
            self.assertEqual(exit_code, 0)
            explanation = json.loads(output)
            self.assertEqual(explanation["finding"]["id"], finding["id"])
            self.assertEqual(
                explanation["artifact_liveness"][0]["dimensions"]["runtime_access"]["status"],
                "UNKNOWN",
            )

    def test_diff_is_read_only_and_lists_new_and_resolved_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root)
            self.assertEqual(self._run(["scan", str(root)])[0], 0)
            self.assertEqual(
                self._run(["baseline", "--root", str(root), "--update"])[0],
                0,
            )
            (root / "plan.md").write_text("FIXME changed commitment\n", encoding="utf-8")
            self.assertEqual(self._run(["scan", str(root)])[0], 0)
            report_path = root / "reports" / "latest.json"
            baseline_path = root / "reference" / "baseline.json"
            before = (report_path.read_bytes(), baseline_path.read_bytes())

            exit_code, output, error = self._run(["diff", "--root", str(root), "--json"])
            after = (report_path.read_bytes(), baseline_path.read_bytes())
            self.assertEqual(exit_code, 0)
            self.assertEqual(error, "")
            self.assertEqual(before, after)
            diff = json.loads(output)
            self.assertEqual(diff["trend"]["new"], 1)
            self.assertEqual(diff["trend"]["resolved"], 1)
            self.assertEqual(len(diff["new_findings"]), 1)
            self.assertEqual(len(diff["resolved_findings"]), 1)
            self.assertIn("not artifact value", diff["verdict_boundary"])


if __name__ == "__main__":
    unittest.main()
