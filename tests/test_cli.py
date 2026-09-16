from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repogc.cli import main


class CliTests(unittest.TestCase):
    def test_scan_writes_reports_but_not_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("TODO explain behavior\n", encoding="utf-8")
            (root / "repogc.toml").write_text(
                """
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
tokens = ["TODO"]

[reports]
markdown = "reports/latest.md"
json = "reports/latest.json"
baseline = "reference/baseline.json"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            exit_code = main(["scan", str(root)])
            self.assertEqual(exit_code, 0)
            self.assertTrue((root / "reports" / "latest.md").exists())
            report = json.loads((root / "reports" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(report["metadata"]["reliability"], "RELIABLE")
            self.assertFalse((root / "reference" / "baseline.json").exists())

    def test_explicit_baseline_update_accepts_reliable_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("TODO explain behavior\n", encoding="utf-8")
            (root / "repogc.toml").write_text(
                """
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
tokens = ["TODO"]

[reports]
markdown = "reports/latest.md"
json = "reports/latest.json"
baseline = "reference/baseline.json"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(main(["scan", str(root)]), 0)
            self.assertEqual(main(["baseline", "--root", str(root), "--update"]), 0)
            self.assertTrue((root / "reference" / "baseline.json").exists())


if __name__ == "__main__":
    unittest.main()
