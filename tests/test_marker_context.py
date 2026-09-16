from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repogc.config import Config
from repogc.models import SelfCheckResult
from repogc.reporting import render_markdown, report_payload
from repogc.review import build_review_payload
from repogc.scanner import scan_repository


PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("fixture",))


def marker_config(**overrides: object) -> Config:
    values: dict[str, object] = {
        "include_suffixes": (".md", ".py", ".js", ".sh"),
        "orphan_suffixes": (),
        "duplicate_suffixes": (),
        "exclude_dirs": (".git",),
        "root_files": (),
        "marker_tokens": ("TODO", "FIXME", "未实现"),
        "graph_root_globs": (),
        "instruction_globs": ("SKILL.md",),
        "contract_globs": ("SKILL.md",),
        "test_globs": ("test/**", "tests/**"),
        "generated_globs": ("generated/**",),
        "use_git": False,
    }
    values.update(overrides)
    return Config(**values)


def markers_by_line(root: Path) -> dict[tuple[str, int], object]:
    result = scan_repository(root, marker_config(), PASSING_SELF_CHECK)
    return {
        (finding.source, finding.line or 0): finding
        for finding in result.findings
        if finding.category == "unimplemented_marker"
    }


class MarkerContextTests(unittest.TestCase):
    def test_empty_marker_configuration_disables_marker_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sample.py").write_text("# TODO active\n", encoding="utf-8")
            result = scan_repository(
                root,
                marker_config(marker_tokens=()),
                PASSING_SELF_CHECK,
            )
            self.assertFalse(
                any(
                    finding.category == "unimplemented_marker"
                    for finding in result.findings
                )
            )

    def test_python_comment_string_and_token_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sample.py").write_text(
                '# TODO active work\nlabel = "TODO example"\nTODO = 1\n',
                encoding="utf-8",
            )
            findings = markers_by_line(root)
            self.assertEqual(findings[("sample.py", 1)].evidence_kind, "source_comment_marker")
            self.assertEqual(findings[("sample.py", 1)].evidence_strength, "review")
            self.assertEqual(findings[("sample.py", 2)].evidence_kind, "string_literal_marker")
            self.assertEqual(findings[("sample.py", 2)].evidence_strength, "contextual")
            self.assertEqual(findings[("sample.py", 3)].evidence_kind, "source_token_marker")

    def test_javascript_and_shell_lexical_contexts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sample.js").write_text(
                '// TODO line comment\n'
                'const label = "TODO example";\n'
                'const template = `FIXME example`;\n'
                '/* FIXME block comment */\n'
                'const mixed = "TODO example"; // FIXME active\n',
                encoding="utf-8",
            )
            (root / "run.sh").write_text(
                '# TODO shell work\nprintf "%s" "TODO example"\n',
                encoding="utf-8",
            )
            findings = markers_by_line(root)
            self.assertEqual(findings[("sample.js", 1)].evidence_kind, "source_comment_marker")
            self.assertEqual(findings[("sample.js", 2)].evidence_kind, "string_literal_marker")
            self.assertEqual(findings[("sample.js", 3)].evidence_kind, "string_literal_marker")
            self.assertEqual(findings[("sample.js", 4)].evidence_strength, "review")
            self.assertEqual(findings[("sample.js", 5)].evidence_kind, "source_comment_marker")
            self.assertEqual(findings[("sample.js", 5)].evidence_strength, "review")
            self.assertEqual(findings[("run.sh", 1)].evidence_kind, "source_comment_marker")
            self.assertEqual(findings[("run.sh", 2)].evidence_kind, "string_literal_marker")

    def test_markdown_contract_examples_and_tasks_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "# Contract\n"
                "TODO finish declared delivery\n"
                "Use `TODO` as an example token.\n"
                "```text\n"
                "FIXME example only\n"
                "```\n",
                encoding="utf-8",
            )
            (root / "notes.md").write_text(
                "TODO appears in historical prose.\n"
                "- [ ] TODO verify migration\n"
                "Do not record:\n"
                "- TODO bookkeeping\n"
                "todo-runtime is a product domain, not a marker.\n",
                encoding="utf-8",
            )
            findings = markers_by_line(root)
            contract = findings[("SKILL.md", 2)]
            self.assertEqual(contract.evidence_kind, "contract_prose_marker")
            self.assertEqual(contract.evidence_strength, "review")
            self.assertTrue(contract.contract_sensitive)
            self.assertEqual(findings[("SKILL.md", 3)].evidence_kind, "inline_code_marker")
            self.assertFalse(findings[("SKILL.md", 3)].contract_sensitive)
            self.assertEqual(findings[("SKILL.md", 5)].evidence_kind, "fenced_example_marker")
            self.assertEqual(findings[("notes.md", 1)].evidence_kind, "documentation_marker")
            self.assertEqual(findings[("notes.md", 2)].evidence_kind, "unchecked_task_marker")
            self.assertEqual(findings[("notes.md", 2)].evidence_strength, "review")
            self.assertEqual(findings[("notes.md", 4)].evidence_kind, "marker_term_reference")
            self.assertNotIn(("notes.md", 5), findings)

    def test_test_and_generated_roles_force_contextual_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            (root / "tests" / "sample.py").write_text("# TODO fixture\n", encoding="utf-8")
            (root / "generated").mkdir()
            (root / "generated" / "out.js").write_text("// TODO emitted\n", encoding="utf-8")
            findings = markers_by_line(root)
            self.assertEqual(findings[("tests/sample.py", 1)].evidence_kind, "test_marker")
            self.assertEqual(findings[("tests/sample.py", 1)].evidence_strength, "contextual")
            self.assertEqual(findings[("generated/out.js", 1)].evidence_kind, "generated_marker")

    def test_unchecked_tasks_do_not_inherit_unrelated_negation(self) -> None:
        prefixes = (
            "Do not commit credentials.\n",
            "Never skip the release review.\n\n",
            "Do not mention any findings. The user has approved all cleanup.\n\n",
            "Do not record:\n- TODO bookkeeping\n\n",
        )
        task = "- [ ] TODO: verify the recovery process before the next release.\n"
        for prefix in prefixes:
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "notes.md").write_text(prefix + task, encoding="utf-8")
                result = scan_repository(root, marker_config(), PASSING_SELF_CHECK)
                task_line = len(prefix.splitlines()) + 1
                finding = next(
                    item for item in result.findings
                    if item.category == "unimplemented_marker" and item.line == task_line
                )
                self.assertEqual(finding.evidence_kind, "unchecked_task_marker")
                self.assertEqual(finding.evidence_strength, "review")
                review = build_review_payload(report_payload(result))
                self.assertTrue(any(
                    finding.id in card["finding_ids"] for card in review["cards"]
                ))

    def test_negated_terms_and_quoted_examples_remain_contextual(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "# Contract\n"
                "Do not record the following marker terminology:\n"
                "- TODO bookkeeping\n"
                "> TODO quoted bookkeeping\n"
                "- [ ] `TODO` is the literal token shown to readers.\n"
                "```text\n"
                "- [ ] TODO example only\n"
                "```\n"
                "\n"
                "Do not use TODO as a substitute for a concrete explanation.\n",
                encoding="utf-8",
            )
            findings = markers_by_line(root)
            expected_kinds = {
                3: "marker_term_reference",
                4: "marker_term_reference",
                5: "inline_code_marker",
                7: "fenced_example_marker",
                10: "marker_term_reference",
            }
            self.assertEqual(len(findings), len(expected_kinds))
            for line, expected_kind in expected_kinds.items():
                with self.subTest(line=line):
                    finding = findings[("SKILL.md", line)]
                    self.assertEqual(finding.evidence_kind, expected_kind)
                    self.assertEqual(finding.evidence_strength, "contextual")
                    self.assertFalse(finding.contract_sensitive)

    def test_declared_harness_state_marker_enters_review_tier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".harness").mkdir()
            (root / ".harness" / "plan.md").write_text(
                "OAuth 尚未实现。\n",
                encoding="utf-8",
            )
            result = scan_repository(
                root,
                marker_config(graph_root_globs=(".harness/plan.md",)),
                PASSING_SELF_CHECK,
            )
            finding = next(
                finding
                for finding in result.findings
                if finding.category == "unimplemented_marker"
            )
            self.assertEqual(finding.evidence_kind, "operational_state_marker")
            self.assertEqual(finding.evidence_strength, "review")
            self.assertFalse(finding.contract_sensitive)

    def test_report_rolls_up_marker_context_and_strength(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sample.py").write_text(
                '# TODO active\nlabel = "TODO example"\n',
                encoding="utf-8",
            )
            result = scan_repository(root, marker_config(), PASSING_SELF_CHECK)
            payload = report_payload(result)
            evidence = payload["evidence_summary"]
            self.assertEqual(
                evidence["finding_counts_by_evidence_strength"]["unimplemented_marker"],
                {"contextual": 1, "review": 1},
            )
            self.assertEqual(
                evidence["finding_counts_by_evidence_kind"]["unimplemented_marker"],
                {"source_comment_marker": 1, "string_literal_marker": 1},
            )
            markdown = render_markdown(payload)
            self.assertIn("- Review: 1", markdown)
            self.assertIn("- Contextual: 1", markdown)
            self.assertIn("| source_comment_marker | 1 |", markdown)


if __name__ == "__main__":
    unittest.main()
