from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from repogc.cli import main
from repogc.config import Config
from repogc.models import SelfCheckResult
from repogc.reporting import report_payload
from repogc.scanner import scan_repository


PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("fixture",))
FIXTURES = Path(__file__).parent / "fixtures"


def graph_config(**overrides: object) -> Config:
    values: dict[str, object] = {
        "include_suffixes": (".md", ".json", ".js"),
        "orphan_suffixes": (".md",),
        "duplicate_suffixes": (),
        "exclude_dirs": (".git",),
        "root_files": ("README.md",),
        "marker_tokens": ("TODO",),
        "graph_root_globs": ("README.md", "SKILL.md", "package.json"),
        "instruction_globs": ("SKILL.md",),
        "contract_globs": ("SKILL.md",),
        "test_globs": ("test/**", "tests/**"),
        "generated_globs": (),
        "ci_globs": (".github/workflows/**",),
        "use_git": False,
    }
    values.update(overrides)
    return Config(**values)


class EvidenceGraphTests(unittest.TestCase):
    def test_repo_scoped_codex_skill_is_a_declared_host_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / ".agents" / "skills" / "review" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("# Review workflow\n", encoding="utf-8")
            result = scan_repository(
                root,
                Config(
                    root_files=(),
                    duplicate_suffixes=(),
                    marker_tokens=(),
                    use_git=False,
                ),
                PASSING_SELF_CHECK,
            )
            artifact = next(
                item
                for item in result.artifacts
                if item.path == ".agents/skills/review/SKILL.md"
            )
            self.assertTrue(artifact.root)
            self.assertTrue(artifact.reachable)
            self.assertEqual(artifact.reachable_from, artifact.path)
            self.assertFalse(
                any(
                    finding.source == artifact.path
                    and finding.category in {"orphan_candidate", "unreachable_candidate"}
                    for finding in result.findings
                )
            )

    def test_skill_contract_makes_process_log_reachable(self) -> None:
        result = scan_repository(
            FIXTURES / "process-log-contract",
            graph_config(root_files=()),
            PASSING_SELF_CHECK,
        )
        process_log = next(
            artifact for artifact in result.artifacts if artifact.path == "process_log.md"
        )
        self.assertTrue(process_log.reachable)
        self.assertEqual(process_log.reachable_from, "SKILL.md")
        self.assertEqual(process_log.evidence_path, ("SKILL.md", "process_log.md"))
        edge = next(edge for edge in result.edges if edge.target == "process_log.md")
        self.assertEqual(edge.kind, "declared_contract_reference")
        self.assertTrue(edge.contract_sensitive)
        self.assertFalse(
            any(
                finding.category == "unreachable_candidate"
                and finding.source == "process_log.md"
                for finding in result.findings
            )
        )
        self.assertFalse(
            any(
                finding.category == "orphan_candidate" and finding.source == "SKILL.md"
                for finding in result.findings
            ),
            "A declared graph root must not also be reported as an orphan.",
        )

    def test_plain_mention_does_not_establish_reachability(self) -> None:
        result = scan_repository(
            FIXTURES / "process-log-unprotected",
            graph_config(),
            PASSING_SELF_CHECK,
        )
        process_log = next(
            artifact for artifact in result.artifacts if artifact.path == "process_log.md"
        )
        self.assertFalse(process_log.reachable)
        edge = next(edge for edge in result.edges if edge.target == "process_log.md")
        self.assertEqual(edge.kind, "path_mention")
        self.assertFalse(edge.traversable)
        self.assertTrue(
            any(
                finding.category == "unreachable_candidate"
                and finding.source == "process_log.md"
                for finding in result.findings
            )
        )
        self.assertFalse(
            any(
                finding.category == "orphan_candidate"
                and finding.source == "process_log.md"
                for finding in result.findings
            ),
            "The old boolean inbound rule sees the mention; the typed graph must still expose non-reachability.",
        )

    def test_test_reference_is_contextual_not_production_reachability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "contract.md").write_text("# Contract\n", encoding="utf-8")
            (root / "test").mkdir()
            (root / "test" / "fixture.md").write_text(
                "Load docs/contract.md\n",
                encoding="utf-8",
            )
            result = scan_repository(root, graph_config(), PASSING_SELF_CHECK)
            edge = next(edge for edge in result.edges if edge.target == "docs/contract.md")
            self.assertEqual(edge.kind, "test_reference")
            self.assertFalse(edge.traversable)
            contract = next(
                artifact for artifact in result.artifacts if artifact.path == "docs/contract.md"
            )
            self.assertFalse(contract.reachable)
            self.assertFalse(
                any(
                    finding.category == "orphan_candidate"
                    and finding.source == "test/fixture.md"
                    for finding in result.findings
                )
            )

    def test_config_entrypoint_and_source_import_form_reachable_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_text(
                '{"main":"./src/index.js"}\n',
                encoding="utf-8",
            )
            (root / "src").mkdir()
            (root / "src" / "index.js").write_text(
                "import './runtime.js';\n",
                encoding="utf-8",
            )
            (root / "src" / "runtime.js").write_text("export const ready = true;\n", encoding="utf-8")
            result = scan_repository(root, graph_config(root_files=()), PASSING_SELF_CHECK)
            artifacts = {artifact.path: artifact for artifact in result.artifacts}
            self.assertTrue(artifacts["src/index.js"].reachable)
            self.assertTrue(artifacts["src/runtime.js"].reachable)
            self.assertEqual(
                artifacts["src/runtime.js"].evidence_path,
                ("package.json", "src/index.js", "src/runtime.js"),
            )
            kinds = {edge.kind for edge in result.edges}
            self.assertIn("config_reference", kinds)
            self.assertIn("source_import", kinds)

    def test_missing_import_is_typed_but_cannot_become_reachable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_text(
                '{"main":"./src/index.js"}\n',
                encoding="utf-8",
            )
            (root / "src").mkdir()
            (root / "src" / "index.js").write_text(
                "import './missing.js';\nimport './missing.js';\n",
                encoding="utf-8",
            )
            result = scan_repository(root, graph_config(root_files=()), PASSING_SELF_CHECK)
            missing = next(
                artifact for artifact in result.artifacts if artifact.path == "src/missing.js"
            )
            self.assertFalse(missing.exists)
            self.assertFalse(missing.reachable)
            edge = next(edge for edge in result.edges if edge.target == "src/missing.js")
            self.assertEqual(edge.kind, "source_import")
            self.assertEqual(edge.strength, "strong")
            payload = report_payload(result)
            self.assertEqual(payload["evidence_summary"]["strong_missing_target_edges"], 1)

    def test_harness_json_root_propagates_machine_state_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".harness").mkdir()
            (root / ".harness" / "task-board.json").write_text(
                '{\n'
                '  "title": "mentions .harness/not-real.md",\n'
                '  "artifacts": [\n'
                '    ".harness/design.md"\n'
                '  ]\n'
                '}\n',
                encoding="utf-8",
            )
            (root / ".harness" / "compact-state.json").write_text(
                '{"artifacts":[".harness/design.md"],'
                '"title":"mentions .harness/compact-not-real.md"}\n',
                encoding="utf-8",
            )
            (root / ".harness" / "design.md").write_text("# Design\n", encoding="utf-8")
            result = scan_repository(
                root,
                graph_config(
                    root_files=(),
                    graph_root_globs=(
                        ".harness/task-board.json",
                        ".harness/compact-state.json",
                    ),
                ),
                PASSING_SELF_CHECK,
            )
            artifacts = {artifact.path: artifact for artifact in result.artifacts}
            self.assertEqual(artifacts[".harness/task-board.json"].role, "harness_state")
            self.assertTrue(artifacts[".harness/design.md"].reachable)
            edge = next(edge for edge in result.edges if edge.target == ".harness/design.md")
            self.assertEqual(edge.kind, "state_reference")
            title_edge = next(
                edge for edge in result.edges if edge.target == ".harness/not-real.md"
            )
            self.assertEqual(title_edge.kind, "path_mention")
            self.assertFalse(title_edge.traversable)
            compact_artifact_edge = next(
                edge
                for edge in result.edges
                if edge.source == ".harness/compact-state.json"
                and edge.target == ".harness/design.md"
            )
            self.assertEqual(compact_artifact_edge.kind, "state_reference")
            compact_title_edge = next(
                edge
                for edge in result.edges
                if edge.target == ".harness/compact-not-real.md"
            )
            self.assertEqual(compact_title_edge.kind, "path_mention")

    def test_fenced_instruction_example_is_contextual(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "# Contract\n\nSuggested layout:\n\n```text\nprocess_log.md\n```\n",
                encoding="utf-8",
            )
            result = scan_repository(root, graph_config(root_files=()), PASSING_SELF_CHECK)
            edge = next(edge for edge in result.edges if edge.target == "process_log.md")
            self.assertEqual(edge.kind, "example_reference")
            self.assertEqual(edge.strength, "contextual")
            self.assertFalse(edge.traversable)
            self.assertFalse(edge.contract_sensitive)

    def test_coverage_separates_checked_and_unobserved_surfaces(self) -> None:
        result = scan_repository(
            FIXTURES / "process-log-contract",
            graph_config(root_files=()),
            PASSING_SELF_CHECK,
        )
        surfaces = {
            item["name"]: item["status"] for item in result.coverage["surfaces"]
        }
        self.assertEqual(result.scan_integrity, "PASS")
        self.assertEqual(result.coverage["status"], "LIMITED")
        self.assertEqual(surfaces["markdown_links"], "CHECKED")
        self.assertEqual(surfaces["dynamic_consumers"], "NOT_OBSERVED")
        self.assertEqual(surfaces["business_meaning"], "NOT_INFERRED")

    def test_evidence_summary_exposes_marker_role_and_contract_sensitivity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "# Contract\nTODO decide whether this remains active\n",
                encoding="utf-8",
            )
            result = scan_repository(root, graph_config(root_files=()), PASSING_SELF_CHECK)
            summary = report_payload(result)["evidence_summary"]
            self.assertEqual(
                summary["finding_counts_by_role"]["unimplemented_marker"]["skill"],
                1,
            )
            self.assertEqual(
                summary["contract_sensitive_findings_by_category"]["unimplemented_marker"],
                1,
            )

    def test_cli_no_write_leaves_target_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["scan", str(root), "--no-write"])
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(exit_code, 0)
            self.assertEqual(before, after)
            self.assertIn("Reports: not written", output.getvalue())


if __name__ == "__main__":
    unittest.main()
