from __future__ import annotations

import tomllib
import unittest
from dataclasses import replace
from pathlib import Path

from repogc.config import load_config
from repogc.models import SelfCheckResult
from repogc.scanner import scan_repository


ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DOCUMENTS = (
    "AGENTS.md",
    "docs/NORTH_STAR.md",
    "docs/CONSTITUTION.md",
)


class ProjectContractTests(unittest.TestCase):
    def test_package_declares_installable_cli_without_runtime_dependencies(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["scripts"]["repogc"], "repogc.cli:main")

    def test_ci_covers_declared_platforms_and_report_only_dogfood(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("macos-latest", workflow)
        self.assertNotIn("windows-latest", workflow)
        self.assertIn("actions/checkout@v7", workflow)
        self.assertIn("actions/setup-python@v7", workflow)
        self.assertIn("repogc scan . --config repogc.toml --no-write", workflow)
        self.assertIn("python -m build", workflow)
        self.assertIn("repogc review examples/first-review", workflow)
        self.assertIn("python -m evals.run", workflow)

    def test_required_public_document_skeleton_exists(self) -> None:
        required = (
            "README.md",
            "docs/first-review.md",
            *GOVERNANCE_DOCUMENTS,
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CHANGELOG.md",
            "docs/architecture.md",
            "docs/audit-index.md",
            "docs/annotations.md",
            "docs/configuration.md",
            "docs/findings.md",
            "docs/privacy.md",
            "docs/report-schema.md",
        )
        self.assertEqual(
            [path for path in required if not (ROOT / path).is_file()],
            [],
        )

    def test_source_distribution_manifest_includes_test_fixtures(self) -> None:
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("recursive-include tests *.py *.md *.json", manifest)
        self.assertIn("recursive-include .agents/skills *.md *.yaml", manifest)
        self.assertIn("recursive-include evals *.py *.json *.md", manifest)
        self.assertIn("include docs/ENGINEERING_AND_EVALUATION.md", manifest)
        self.assertIn("include docs/evidence-bundle.md", manifest)
        self.assertIn("include .github/workflows/ci.yml", manifest)
        self.assertIn("recursive-include examples *.md *.toml", manifest)
        for path in GOVERNANCE_DOCUMENTS:
            with self.subTest(path=path):
                self.assertIn(f"include {path}", manifest.splitlines())

    def test_repo_scoped_codex_review_skill_is_complete(self) -> None:
        skill = ROOT / ".agents" / "skills" / "repogc-review" / "SKILL.md"
        metadata = skill.parent / "agents" / "openai.yaml"
        self.assertTrue(skill.is_file())
        self.assertTrue(metadata.is_file())
        text = skill.read_text(encoding="utf-8")
        self.assertNotIn("TODO", text)
        self.assertIn("openai-codex-interactive", text)
        self.assertIn("repogc review", text)


class GovernanceDocumentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config, _ = load_config(ROOT)
        cls.result = scan_repository(
            ROOT,
            replace(config, use_git=False),
            SelfCheckResult(ok=True, checks=("fixture",)),
        )
        cls.artifacts = {artifact.path: artifact for artifact in cls.result.artifacts}

    def test_agent_entry_links_to_scanned_reachable_governance_documents(self) -> None:
        entry = self.artifacts["AGENTS.md"]
        self.assertTrue(entry.root)
        self.assertTrue(entry.scanned)
        self.assertTrue(entry.reachable)
        for path in GOVERNANCE_DOCUMENTS[1:]:
            with self.subTest(path=path):
                artifact = self.artifacts[path]
                self.assertTrue(artifact.exists)
                self.assertTrue(artifact.scanned)
                self.assertTrue(artifact.reachable)
                self.assertTrue(
                    any(
                        edge.source == entry.path
                        and edge.target == path
                        and edge.syntax == "markdown_link"
                        and edge.strength == "strong"
                        and edge.traversable
                        for edge in self.result.edges
                    ),
                    f"AGENTS.md must link directly to {path} with a traversable edge.",
                )

    def test_readme_entry_and_governance_file_links_resolve(self) -> None:
        linked_from_readme = {
            edge.target
            for edge in self.result.edges
            if edge.source == "README.md" and edge.syntax == "markdown_link"
        }
        self.assertTrue(set(GOVERNANCE_DOCUMENTS) <= linked_from_readme)
        sources = {"README.md", *GOVERNANCE_DOCUMENTS}
        broken_links = [
            (edge.source, edge.line, edge.target)
            for edge in self.result.edges
            if edge.source in sources
            and edge.syntax == "markdown_link"
            and not self.artifacts[edge.target].exists
        ]
        self.assertEqual(broken_links, [])


if __name__ == "__main__":
    unittest.main()
