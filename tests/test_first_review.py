from pathlib import Path
import subprocess
import sys
import unittest

from repogc.config import load_config
from repogc.models import SelfCheckResult
from repogc.scanner import scan_repository


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "first-review"


class FirstReviewTests(unittest.TestCase):
    def test_demo_observations_do_not_establish_removal(self):
        config, _ = load_config(DEMO)
        result = scan_repository(DEMO, config, SelfCheckResult(ok=True, checks=("fixture",)))
        edges = result.edges
        self.assertTrue(any(e.source == "README.md" and e.target == "docs/setup.md" for e in edges))
        artifacts = {a.path: a for a in result.artifacts}
        self.assertFalse(artifacts["docs/setup.md"].exists)
        self.assertTrue(artifacts["docs/offline-export.md"].exists)
        self.assertFalse(artifacts["docs/offline-export.md"].reachable)
        self.assertIn("Retain the design", (DEMO / "docs/roadmap.md").read_text())

    def test_documented_review_is_read_only(self):
        before = {p.relative_to(DEMO): p.read_bytes() for p in DEMO.rglob("*") if p.is_file()}
        run = subprocess.run([sys.executable, "-m", "repogc", "review", str(DEMO)],
                             capture_output=True, text=True, check=True)
        self.assertIn("Read-only", run.stdout)
        after = {p.relative_to(DEMO): p.read_bytes() for p in DEMO.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
