"""Template text that was never replaced.

Rules match editorial instructions addressed to whoever sets up a repository
(for example the GitHub and Contributor Covenant templates). Instructions
addressed to readers, such as "replace <your-token>", are deliberately not
matched. Code, comments and template files themselves are not inspected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from repogc.markdown_text import is_markdown, prose_lines


PLACEHOLDER_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "unedited_template_notice",
        re.compile(r"has not (?:yet )?(?:been )?edited this file", re.IGNORECASE),
    ),
    (
        "maintainer_directive",
        re.compile(r"\b(?:REPO|REPOSITORY|PROJECT) (?:OWNER|MAINTAINER)S?\b\**\s*:"),
    ),
    ("insert_here", re.compile(r"\bINSERT\b[^\n]{0,80}?\bHERE\b")),
    ("product_name_placeholder", re.compile(r"\bPROJECT or PRODUCT\b")),
    (
        "bracket_placeholder",
        re.compile(
            r"\[(?:INSERT|ENTER)\b[^\]\n]{0,60}\]"
            r"|\[(?:PROJECT|PRODUCT|REPO|REPOSITORY|COMPANY|ORGANIZATION) NAME\]"
        ),
    ),
    ("lorem_ipsum", re.compile(r"\blorem ipsum dolor\b", re.IGNORECASE)),
    (
        "chinese_fill_in",
        re.compile(
            r"[【\[]\s*请?(?:在此|此处)(?:填写|替换|插入)[^】\]\n]{0,30}[】\]]"
            r"|【\s*请填写[^】\n]{0,30}】"
        ),
    ),
)


@dataclass(frozen=True)
class PlaceholderHit:
    line: int
    rule: str
    text: str


def is_template_file(path: str) -> bool:
    """Template files are meant to contain placeholders."""
    return any("template" in part.lower() for part in PurePosixPath(path).parts)


def find_placeholders(path: str, text: str) -> list[PlaceholderHit]:
    if not is_markdown(path) or is_template_file(path):
        return []
    hits: list[PlaceholderHit] = []
    original = text.splitlines()
    for line_number, line in enumerate(prose_lines(text), start=1):
        if not line.strip():
            continue
        for rule, pattern in PLACEHOLDER_RULES:
            if pattern.search(line):
                hits.append(
                    PlaceholderHit(
                        line=line_number,
                        rule=rule,
                        text=original[line_number - 1].strip(),
                    )
                )
                break
    return hits
