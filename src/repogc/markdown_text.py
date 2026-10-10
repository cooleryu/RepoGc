"""The parts of Markdown that decide what is rendered prose and what is a link.

Only the structure needed for confident claims is modelled: front matter,
fenced and indented code, inline code spans, HTML comments, inline links and
images, reference definitions and HTML ``href``/``src`` attributes. Anything the
reader does not support is skipped, never guessed.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from urllib.parse import unquote


MARKDOWN_SUFFIXES = (".md", ".markdown")

FENCE_OPEN = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])(?:\s|$)")
REFERENCE_DEFINITION = re.compile(
    r"^ {0,3}\[(?P<label>(?:[^\]\\]|\\.)+)\]:[ \t]*"
    r"(?:<(?P<angle>[^>\n]*)>|(?P<bare>\S+))"
)
HTML_LINK_ATTRIBUTE = re.compile(
    r"<(?:a|img|source)\b[^>]*?\b(?:href|src)\s*=\s*"
    r"(?:\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)')",
    re.IGNORECASE,
)
URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
TEMPLATE_CHARACTERS = ("{", "}", "$")


@dataclass(frozen=True)
class MarkdownLink:
    line: int
    column: int
    destination: str
    syntax: str


def is_markdown(path: str) -> bool:
    return path.lower().endswith(MARKDOWN_SUFFIXES)


def _blank(text: str) -> str:
    return " " * len(text)


def _closes_fence(line: str, fence: str) -> bool:
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3:
        return False
    run = len(stripped) - len(stripped.lstrip(fence[0]))
    return run >= len(fence) and not stripped[run:].strip()


def _mask_code_spans(line: str) -> str:
    """Blank inline code spans; an unmatched backtick run stays literal."""
    characters = list(line)
    index = 0
    while index < len(line):
        if line[index] == "\\":
            index += 2
            continue
        if line[index] != "`":
            index += 1
            continue
        run_end = index
        while run_end < len(line) and line[run_end] == "`":
            run_end += 1
        width = run_end - index
        search = run_end
        closing = -1
        while search < len(line):
            if line[search] != "`":
                search += 1
                continue
            candidate_end = search
            while candidate_end < len(line) and line[candidate_end] == "`":
                candidate_end += 1
            if candidate_end - search == width:
                closing = candidate_end
                break
            search = candidate_end
        if closing == -1:
            index = run_end
            continue
        for position in range(index, closing):
            characters[position] = " "
        index = closing
    return "".join(characters)


def prose_lines(text: str) -> list[str]:
    """Return source lines with non-rendered and code regions blanked.

    Blanked characters become spaces, so line numbers and columns still point
    at the original text.
    """
    lines = text.splitlines()
    masked = [""] * len(lines)
    start = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() in {"---", "..."}:
                start = index + 1
                break
    fence: str | None = None
    in_comment = False
    previous_blank = True
    in_indented_code = False
    list_active = False
    for index in range(start, len(lines)):
        line = lines[index]
        if fence is not None:
            if _closes_fence(line, fence):
                fence = None
            previous_blank = False
            continue
        expanded = line.expandtabs(4)
        blank = not line.strip()
        indented = expanded.startswith("    ")
        if blank:
            previous_blank = True
            continue
        if indented and not list_active and (previous_blank or in_indented_code):
            in_indented_code = True
            continue
        in_indented_code = False
        opening = FENCE_OPEN.match(line)
        if opening and not in_comment:
            marker = opening.group("fence")
            if marker[0] != "`" or "`" not in opening.group("info"):
                fence = marker
                previous_blank = False
                continue
        if LIST_ITEM.match(line):
            list_active = True
        elif previous_blank and not indented:
            list_active = False
        previous_blank = False

        line = _mask_code_spans(line)
        visible: list[str] = []
        position = 0
        while position < len(line):
            if in_comment:
                end = line.find("-->", position)
                if end == -1:
                    visible.append(_blank(line[position:]))
                    position = len(line)
                else:
                    visible.append(_blank(line[position : end + 3]))
                    position = end + 3
                    in_comment = False
                continue
            begin = line.find("<!--", position)
            if begin == -1:
                visible.append(line[position:])
                break
            visible.append(line[position:begin])
            position = begin
            in_comment = True
        masked[index] = "".join(visible)
    return masked


def _link_destination(line: str, start: int) -> tuple[str, int] | None:
    """Parse ``destination [title])`` beginning at ``start``; return end index."""
    position = start
    while position < len(line) and line[position] in " \t":
        position += 1
    if position < len(line) and line[position] == "<":
        close = line.find(">", position + 1)
        if close == -1:
            return None
        destination = line[position + 1 : close]
        position = close + 1
    else:
        depth = 0
        begin = position
        while position < len(line):
            character = line[position]
            if character == "\\":
                position += 2
                continue
            if character in " \t":
                break
            if character == "(":
                depth += 1
            elif character == ")":
                if depth == 0:
                    break
                depth -= 1
            position += 1
        if depth != 0:
            return None
        destination = line[begin:position]
    while position < len(line) and line[position] in " \t":
        position += 1
    if position < len(line) and line[position] in "\"'(":
        closing = ")" if line[position] == "(" else line[position]
        end = line.find(closing, position + 1)
        if end == -1:
            return None
        position = end + 1
        while position < len(line) and line[position] in " \t":
            position += 1
    if position >= len(line) or line[position] != ")":
        return None
    return destination, position + 1


def _inline_links(line: str, line_number: int) -> list[MarkdownLink]:
    links: list[MarkdownLink] = []
    openers: list[int] = []
    position = 0
    while position < len(line):
        character = line[position]
        if character == "\\":
            position += 2
            continue
        if character == "[":
            openers.append(position)
        elif character == "]" and openers:
            opener = openers.pop()
            if position + 1 < len(line) and line[position + 1] == "(":
                parsed = _link_destination(line, position + 2)
                if parsed is not None:
                    destination, end = parsed
                    image = opener > 0 and line[opener - 1] == "!"
                    links.append(
                        MarkdownLink(
                            line=line_number,
                            column=opener - 1 if image else opener,
                            destination=destination,
                            syntax="image" if image else "inline",
                        )
                    )
                    if not image:
                        # A link cannot contain another link.
                        openers.clear()
                    position = end
                    continue
        position += 1
    return links


def extract_links(text: str) -> list[MarkdownLink]:
    links: list[MarkdownLink] = []
    for line_number, line in enumerate(prose_lines(text), start=1):
        if not line.strip():
            continue
        definition = REFERENCE_DEFINITION.match(line)
        if definition and not definition.group("label").startswith("^"):
            destination = definition.group("angle")
            if destination is None:
                destination = definition.group("bare")
            links.append(
                MarkdownLink(
                    line=line_number,
                    column=definition.start("label") - 1,
                    destination=destination,
                    syntax="definition",
                )
            )
            continue
        links.extend(_inline_links(line, line_number))
        for match in HTML_LINK_ATTRIBUTE.finditer(line):
            destination = match.group("double")
            if destination is None:
                destination = match.group("single")
            links.append(
                MarkdownLink(
                    line=line_number,
                    column=match.start(),
                    destination=destination,
                    syntax="html",
                )
            )
    return links


def local_link_path(source: str, destination: str) -> str | None:
    """Resolve a link to a repository-relative path, or None when out of scope.

    External URLs, anchors, site-absolute paths, template expressions and
    paths leaving the repository are not checked.
    """
    value = destination.strip()
    if (
        not value
        or value.startswith(("#", "/", "\\"))
        or URI_SCHEME.match(value)
        or any(character in value for character in TEMPLATE_CHARACTERS)
    ):
        return None
    value = value.split("#", 1)[0].split("?", 1)[0]
    value = unquote(value).replace("\\", "/")
    if not value:
        return None
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(source), value))
    if joined == ".." or joined.startswith("../"):
        return None
    return "" if joined == "." else joined
