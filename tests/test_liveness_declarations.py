from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repogc.config import Config, LivenessDeclaration, load_config
from repogc.models import SelfCheckResult
from repogc.reporting import report_payload
from repogc.scanner import scan_repository


PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("fixture",))


class LivenessDeclarationTests(unittest.TestCase):
    def test_config_parses_and_canonicalizes_declarations(self) -> None:
        declarations = """
[[liveness.declarations]]
path = "logs/process.md"
kind = "dynamic_consumer"
source = "case registry"
reason = "Loaded through a computed path"

[[liveness.declarations]]
path = "spec.md"
kind = "retention"
source = "release policy"
reason = "Required audit record"
""".strip()
        reversed_declarations = "\n\n".join(reversed(declarations.split("\n\n")))
        with tempfile.TemporaryDirectory() as left_temp, tempfile.TemporaryDirectory() as right_temp:
            left = Path(left_temp)
            right = Path(right_temp)
            (left / "repogc.toml").write_text(declarations + "\n", encoding="utf-8")
            (right / "repogc.toml").write_text(
                reversed_declarations + "\n",
                encoding="utf-8",
            )
            left_config, _ = load_config(left)
            right_config, _ = load_config(right)
            self.assertEqual(left_config.liveness_declarations, right_config.liveness_declarations)
            self.assertEqual(left_config.digest(), right_config.digest())
            self.assertEqual(
                [item.path for item in left_config.liveness_declarations],
                ["logs/process.md", "spec.md"],
            )

    def test_invalid_declarations_are_rejected(self) -> None:
        cases = (
            ("/absolute.md", "retention"),
            ("C:/absolute.md", "retention"),
            ("../escape.md", "retention"),
            ("artifact.md", "deletion_verdict"),
        )
        for path, kind in cases:
            with self.subTest(path=path, kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "repogc.toml").write_text(
                    "\n".join(
                        (
                            "[[liveness.declarations]]",
                            f'path = "{path}"',
                            f'kind = "{kind}"',
                            'source = "fixture"',
                            'reason = "fixture reason"',
                            "",
                        )
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    load_config(root)

    def test_declaration_enriches_profile_without_suppressing_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            (root / "process_log.md").write_text(
                "TODO preserve runtime narrative\n",
                encoding="utf-8",
            )
            base = dict(
                include_suffixes=(".md",),
                orphan_suffixes=(".md",),
                duplicate_suffixes=(),
                exclude_dirs=(".git",),
                root_files=("README.md",),
                marker_tokens=("TODO",),
                graph_root_globs=("README.md",),
                use_git=False,
            )
            without = scan_repository(root, Config(**base), PASSING_SELF_CHECK)
            with_declaration = scan_repository(
                root,
                Config(
                    **base,
                    liveness_declarations=(
                        LivenessDeclaration(
                            path="process_log.md",
                            kind="dynamic_consumer",
                            source="case registry",
                            reason="Loaded through a computed case path.",
                        ),
                        LivenessDeclaration(
                            path="unmatched.md",
                            kind="retention",
                            source="fixture policy",
                            reason="Does not match a current review subject.",
                        ),
                    ),
                ),
                PASSING_SELF_CHECK,
            )
            self.assertEqual(without.category_counts(), with_declaration.category_counts())
            artifact = next(
                item for item in with_declaration.artifacts if item.path == "process_log.md"
            )
            self.assertFalse(artifact.reachable)

            payload = report_payload(with_declaration)
            profile = next(
                item for item in payload["artifact_liveness"] if item["path"] == "process_log.md"
            )
            self.assertEqual(profile["dimensions"]["dynamic_consumers"]["status"], "DECLARED")
            self.assertIn("case registry", profile["dimensions"]["dynamic_consumers"]["evidence"])
            self.assertEqual(payload["liveness_declarations"]["count"], 2)
            self.assertEqual(len(payload["liveness_declarations"]["matched"]), 1)
            self.assertEqual(len(payload["liveness_declarations"]["unmatched"]), 1)
            surfaces = {
                item["name"]: item["status"]
                for item in payload["metadata"]["coverage"]["surfaces"]
            }
            self.assertEqual(surfaces["dynamic_consumers"], "DECLARATIONS_ONLY")


if __name__ == "__main__":
    unittest.main()
