from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repogc.config import Config
from repogc.markdown_text import extract_links, local_link_path, prose_lines
from repogc.models import SelfCheckResult
from repogc.placeholders import find_placeholders
from repogc.scanner import scan_repository


PASSING_SELF_CHECK = SelfCheckResult(ok=True, checks=("fixture",))

# MarkItDown SUPPORT.md at b8f79c57ebc0044be41323d89b2a45d3fda8460e, lines 1-25.
MARKITDOWN_SUPPORT = """# TODO: The maintainer of this repo has not yet edited this file

**REPO OWNER**: Do you want Customer Service & Support (CSS) support for this product/project?

- **No CSS support:** Fill out this template with information about how to file issues and get help.
- **Yes CSS support:** Fill out an intake form at [aka.ms/onboardsupport](https://aka.ms/onboardsupport). CSS will work with/help you to determine next steps.
- **Not sure?** Fill out an intake as though the answer were "Yes". CSS will help you decide.

*Then remove this first heading from this SUPPORT.MD file before publishing your repo.*

# Support

## How to file issues and get help

This project uses GitHub Issues to track bugs and feature requests. Please search the existing
issues before filing new issues to avoid duplicates.  For new issues, file your bug or
feature request as a new Issue.

For help and questions about using this project, please **REPO MAINTAINER: INSERT INSTRUCTIONS HERE
FOR HOW TO ENGAGE REPO OWNERS OR COMMUNITY FOR HELP. COULD BE A STACK OVERFLOW TAG OR OTHER
CHANNEL. WHERE WILL YOU HELP PEOPLE?**.

## Microsoft Support Policy

Support for this **PROJECT or PRODUCT** is limited to the resources listed above.
"""


def destinations(text: str) -> list[str]:
    return [link.destination for link in extract_links(text)]


def broken(root: Path, **overrides: object) -> list[tuple[str, int | None, str | None, str]]:
    overrides.setdefault("use_git", False)
    config = Config(duplicate_suffixes=(), **overrides)
    result = scan_repository(root, config, PASSING_SELF_CHECK)
    return sorted(
        (item.source, item.line, item.target, item.rule)
        for item in result.findings
        if item.category == "broken_reference"
    )


def write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class MarkdownLinkExtractionTests(unittest.TestCase):
    def test_link_kinds(self) -> None:
        text = (
            "See [guide](docs/guide.md \"Guide\") and ![logo](img/logo.png).\n"
            "[ref]: docs/ref.md\n"
            "[^1]: A footnote, not a link.\n"
            '<img src="img/hero.png"> <a href=\'docs/a.md\'>a</a>\n'
            "[paren](docs/file(1).md) [angle](<docs/with space.md>)\n"
        )
        self.assertEqual(
            destinations(text),
            [
                "docs/guide.md",
                "img/logo.png",
                "docs/ref.md",
                "img/hero.png",
                "docs/a.md",
                "docs/file(1).md",
                "docs/with space.md",
            ],
        )

    def test_code_comments_and_front_matter_are_not_links(self) -> None:
        text = (
            "---\n"
            "link: [front](front.md)\n"
            "---\n"
            "Inline `[code](code.md)` stays code.\n"
            "``` markdown\n"
            "[fenced](fenced.md)\n"
            "```\n"
            "\n"
            "    [indented](indented.md)\n"
            "\n"
            "<!-- [comment](comment.md)\n"
            "still [comment](comment2.md) -->\n"
            "~~~~\n"
            "[tilde](tilde.md)\n"
            "~~~~\n"
            "\\[escaped](escaped.md)\n"
            "[real](real.md)\n"
        )
        self.assertEqual(destinations(text), ["real.md"])

    def test_code_that_looks_like_paths_is_not_a_link(self) -> None:
        text = (
            "assert actual.markdown == expected.markdown\n"
            "Save the output as `report.md`; the name is up to you.\n"
            "Required delivery artifact: process_log.md\n"
        )
        self.assertEqual(destinations(text), [])

    def test_list_continuation_is_prose_not_code(self) -> None:
        text = "- Item\n\n    [nested](nested.md)\n"
        self.assertEqual(destinations(text), ["nested.md"])

    def test_columns_survive_masking(self) -> None:
        line = "`x` [a](b.md)"
        self.assertEqual(len(prose_lines(line)[0]), len(line))
        self.assertEqual(extract_links(line)[0].column, 4)

    def test_out_of_scope_destinations(self) -> None:
        for destination in (
            "https://example.com/a.md",
            "mailto:team@example.com",
            "#section",
            "/docs/site-root.md",
            "{{ page.url }}",
            "${BASE}/a.md",
            "../../outside.md",
            "",
        ):
            with self.subTest(destination=destination):
                self.assertIsNone(local_link_path("docs/index.md", destination))

    def test_relative_resolution(self) -> None:
        self.assertEqual(local_link_path("docs/index.md", "guide.md#top"), "docs/guide.md")
        self.assertEqual(local_link_path("docs/index.md", "../README.md?x=1"), "README.md")
        self.assertEqual(local_link_path("docs/index.md", "my%20notes.md"), "docs/my notes.md")
        self.assertEqual(local_link_path("README.md", "./"), "")


class BrokenLinkScanTests(unittest.TestCase):
    def test_missing_targets_are_reported_and_present_ones_are_not(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root,
                {
                    "README.md": (
                        "[ok](docs/guide.md) [gone](docs/removed.md)\n"
                        "![shot](img/missing.png) [dir](docs/)\n"
                        "[gone again](docs/removed.md)\n"
                        "[ref]: notes/old.md\n"
                    ),
                    "docs/guide.md": "# Guide\n",
                },
            )
            self.assertEqual(
                broken(root),
                [
                    ("README.md", 1, "docs/removed.md", "markdown_link_target_missing"),
                    ("README.md", 2, "img/missing.png", "markdown_link_target_missing"),
                    ("README.md", 4, "notes/old.md", "markdown_link_target_missing"),
                ],
            )

    def test_moved_target_names_its_unique_new_location(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root,
                {
                    "notes/archived/a.md": "[plan](plan.md) [gone](gone.md)\n",
                    "notes/implemented/plan.md": "# Plan\n",
                },
            )
            result = scan_repository(root, Config(use_git=False), PASSING_SELF_CHECK)
            evidence = sorted(
                item.evidence for item in result.findings if item.category == "broken_reference"
            )
            self.assertEqual(
                evidence,
                [
                    "gone.md (not found)",
                    "plan.md (not found; same file name at notes/implemented/plan.md)",
                ],
            )

    def test_root_file_does_not_mask_missing_relative_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, {"docs/index.md": "[setup](setup.md)\n", "setup.md": "# Setup\n"})
            self.assertEqual(
                broken(root),
                [("docs/index.md", 1, "docs/setup.md", "markdown_link_target_missing")],
            )

    def test_case_mismatch_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, {"README.md": "[guide](docs/Guide.md)\n", "docs/guide.md": "# Guide\n"})
            self.assertEqual(
                broken(root),
                [("README.md", 1, "docs/Guide.md", "markdown_link_target_case_mismatch")],
            )

    def test_build_output_targets_are_not_claimed_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, {"README.md": "[api](dist/api.html) [report](docs/gc_reports/latest.md)\n"})
            self.assertEqual(broken(root), [])

    def test_long_targets_with_shared_prefix_stay_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prefix = "docs/decisions/0015-reference-evidence-policy"
            write(root, {"README.md": f"[a]({prefix}-a.md) [b]({prefix}-b.md)\n"})
            self.assertEqual(len(broken(root)), 2)

    def test_test_fixtures_are_not_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root,
                {
                    "tests/fixtures/broken/README.md": "[gone](gone.md) [INSERT CONTACT METHOD]\n",
                    "docs/index.md": "[gone](gone.md)\n",
                },
            )
            self.assertEqual(
                broken(root),
                [("docs/index.md", 1, "docs/gone.md", "markdown_link_target_missing")],
            )

    def test_doc_site_extensionless_links_and_templates_are_not_claimed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root,
                {
                    "docs/index.md": "[agents](remote-agents) [tools](../ref/tools) [nope](nothing)\n",
                    "docs/remote-agents.md": "# Remote\n",
                    "ref/tools/index.md": "# Tools\n",
                    "skills/x/references/preview_template.md": "[latest](latest.md)\n",
                },
            )
            self.assertEqual(
                broken(root),
                [("docs/index.md", 1, "docs/nothing", "markdown_link_target_missing")],
            )

    def test_git_ignored_sources_and_sparse_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root,
                {
                    ".gitignore": "bundle/\n",
                    "README.md": "[guide](docs/guide.md) [gone](docs/gone.md)\n",
                    "docs/guide.md": "# Guide\n",
                    "bundle/copied.md": "[id](issueQuirksModeDoctype)\n",
                },
            )
            git = ["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t"]
            for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
                subprocess.run([*git, *args], check=True, capture_output=True)
            # A sparse or partial checkout leaves tracked files off disk.
            (root / "docs" / "guide.md").unlink()
            self.assertEqual(
                broken(root, use_git=True),
                [("README.md", 1, "docs/gone.md", "markdown_link_target_missing")],
            )

    def test_plain_path_text_never_becomes_a_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root,
                {
                    "SKILL.md": "Write the result to `report.md`.\nRequired: process_log.md\n",
                    "tests/test_x.py": "assert actual.markdown == cell.text\n",
                },
            )
            self.assertEqual(broken(root), [])


class PlaceholderTests(unittest.TestCase):
    def test_markitdown_support_template(self) -> None:
        hits = find_placeholders("SUPPORT.md", MARKITDOWN_SUPPORT)
        self.assertEqual(
            [(hit.line, hit.rule) for hit in hits],
            [
                (1, "unedited_template_notice"),
                (3, "maintainer_directive"),
                (19, "maintainer_directive"),
                (25, "product_name_placeholder"),
            ],
        )

    def test_known_template_forms(self) -> None:
        for text in (
            "Report issues to [INSERT CONTACT METHOD].",
            "Copyright [PROJECT NAME] authors.",
            "Lorem ipsum dolor sit amet.",
            "联系方式：【请在此填写】",
        ):
            with self.subTest(text=text):
                self.assertEqual(len(find_placeholders("docs/a.md", text + "\n")), 1)

    def test_reader_instructions_and_code_are_not_placeholders(self) -> None:
        text = (
            "Replace <your-token> with your token.\n"
            "Clone https://github.com/[your-username]/repo.\n"
            "Run `INSERT YOUR KEY HERE` in the prompt.\n"
            "```\n"
            "[INSERT CONTACT METHOD]\n"
            "```\n"
            "The word lorem ipsum names filler text.\n"
            "<!-- REPO OWNER: fill this in -->\n"
        )
        self.assertEqual(find_placeholders("docs/a.md", text), [])

    def test_template_files_and_non_markdown_are_skipped(self) -> None:
        text = "Contact [INSERT CONTACT METHOD]\n"
        self.assertEqual(find_placeholders(".github/ISSUE_TEMPLATE/bug.md", text), [])
        self.assertEqual(find_placeholders("PULL_REQUEST_TEMPLATE.md", text), [])
        self.assertEqual(find_placeholders("src/app.py", text), [])

    def test_scan_reports_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, {"README.md": "# Demo\n", "SUPPORT.md": MARKITDOWN_SUPPORT})
            result = scan_repository(root, Config(use_git=False), PASSING_SELF_CHECK)
            lines = sorted(
                item.line for item in result.findings if item.category == "placeholder_text"
            )
            self.assertEqual(lines, [1, 3, 19, 25])


if __name__ == "__main__":
    unittest.main()
