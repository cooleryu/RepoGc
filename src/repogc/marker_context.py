from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MarkerHit:
    line: int
    column: int
    line_text: str
    token: str


@dataclass(frozen=True)
class MarkerClassification:
    kind: str
    strength: str
    contract_sensitive: bool = False


SOURCE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".sh"}
JAVASCRIPT_SUFFIXES = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}
DOCUMENT_SUFFIXES = {".md", ".markdown", ".txt"}
CONFIG_SUFFIXES = {".json", ".jsonl", ".toml", ".yaml", ".yml"}
UNCHECKED_TASK_PATTERN = re.compile(r"^\s*[-*+]\s+\[\s\]")
MARKER_NEGATION_PATTERN = re.compile(
    r"\b(?:do\s+not|don't|must\s+not|should\s+not|never|without|no)\b"
    r"|不要|不得|不记录|不使用|不应该|不应|无需|禁止",
    re.IGNORECASE,
)


def _absolute_offsets(text: str, hits: list[MarkerHit]) -> dict[int, MarkerHit]:
    offsets: dict[int, MarkerHit] = {}
    line_starts: list[int] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        line_starts.append(offset)
        offset += len(line)
    if not text or text[-1] in "\r\n":
        line_starts.append(offset)
    for hit in hits:
        if 1 <= hit.line <= len(line_starts):
            offsets[line_starts[hit.line - 1] + hit.column] = hit
    return offsets


def _position_in_token(hit: MarkerHit, token: tokenize.TokenInfo) -> bool:
    start_line, start_column = token.start
    end_line, end_column = token.end
    if hit.line < start_line or hit.line > end_line:
        return False
    if start_line == end_line:
        return start_column <= hit.column < end_column
    if hit.line == start_line:
        return hit.column >= start_column
    if hit.line == end_line:
        return hit.column < end_column
    return True


def _python_contexts(text: str, hits: list[MarkerHit]) -> dict[MarkerHit, str]:
    contexts = {hit: "code" for hit in hits}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for token in tokens:
            if token.type not in {tokenize.COMMENT, tokenize.STRING}:
                continue
            context = "comment" if token.type == tokenize.COMMENT else "string"
            for hit in hits:
                if _position_in_token(hit, token):
                    contexts[hit] = context
    except (IndentationError, SyntaxError, tokenize.TokenError):
        # Partial or intentionally invalid source remains scannable. Any spans
        # tokenized before the error retain their classification.
        pass
    return contexts


def _generic_code_contexts(
    text: str,
    hits: list[MarkerHit],
    *,
    slash_comments: bool,
    hash_comments: bool,
) -> dict[MarkerHit, str]:
    targets = _absolute_offsets(text, hits)
    contexts: dict[MarkerHit, str] = {}
    state = "code"
    quote = ""
    escaped = False
    index = 0
    while index < len(text):
        character = text[index]
        next_character = text[index + 1] if index + 1 < len(text) else ""

        hit = targets.get(index)
        if hit is not None:
            contexts[hit] = "comment" if state in {"line_comment", "block_comment"} else state

        if state == "line_comment":
            if character == "\n":
                state = "code"
            index += 1
            continue
        if state == "block_comment":
            if character == "*" and next_character == "/":
                state = "code"
                index += 2
            else:
                index += 1
            continue
        if state == "string":
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                state = "code"
                quote = ""
            elif character == "\n" and quote != "`":
                state = "code"
                quote = ""
            index += 1
            continue

        if slash_comments and character == "/" and next_character == "/":
            state = "line_comment"
            index += 2
            continue
        if slash_comments and character == "/" and next_character == "*":
            state = "block_comment"
            index += 2
            continue
        if hash_comments and character == "#" and (
            index == 0 or text[index - 1].isspace()
        ):
            state = "line_comment"
            index += 1
            continue
        if character in {"'", '"'} or (slash_comments and character == "`"):
            state = "string"
            quote = character
            index += 1
            continue
        index += 1

    for hit in hits:
        contexts.setdefault(hit, "code")
    return contexts


def _fenced_lines(text: str) -> set[int]:
    fenced: set[int] = set()
    marker: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        current = "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else None
        if marker is not None:
            fenced.add(line_number)
            if current == marker:
                marker = None
        elif current is not None:
            marker = current
            fenced.add(line_number)
    return fenced


def _inside_inline_code(line: str, column: int) -> bool:
    open_width: int | None = None
    for match in re.finditer(r"`+", line):
        if match.start() >= column:
            break
        width = len(match.group(0))
        if open_width is None:
            open_width = width
        elif width == open_width:
            open_width = None
    return open_width is not None


def _inside_html_comment(text: str, hit: MarkerHit) -> bool:
    offsets = _absolute_offsets(text, [hit])
    if not offsets:
        return False
    offset = next(iter(offsets))
    return text.rfind("<!--", 0, offset + 1) > text.rfind("-->", 0, offset + 1)


def _is_marker_term_reference(text: str, hit: MarkerHit) -> bool:
    # An explicit task must not inherit an unrelated preceding prohibition.
    # Fenced and inline-code examples are handled before this predicate.
    if UNCHECKED_TASK_PATTERN.search(hit.line_text[: hit.column]):
        return False
    lines = text.splitlines()
    start = max(0, hit.line - 5)
    window = "\n".join(lines[start : hit.line])
    return MARKER_NEGATION_PATTERN.search(window) is not None


def classify_marker_hits(
    source: str,
    text: str,
    role: str,
    hits: list[MarkerHit],
    *,
    contract_source: bool,
    operational_source: bool,
) -> dict[MarkerHit, MarkerClassification]:
    if role == "test":
        return {
            hit: MarkerClassification("test_marker", "contextual")
            for hit in hits
        }
    if role == "generated":
        return {
            hit: MarkerClassification("generated_marker", "contextual")
            for hit in hits
        }

    suffix = Path(source).suffix.lower()
    if suffix in DOCUMENT_SUFFIXES:
        fenced = _fenced_lines(text)
        classifications: dict[MarkerHit, MarkerClassification] = {}
        for hit in hits:
            if hit.line in fenced:
                classification = MarkerClassification("fenced_example_marker", "contextual")
            elif _inside_inline_code(hit.line_text, hit.column):
                classification = MarkerClassification("inline_code_marker", "contextual")
            elif _is_marker_term_reference(text, hit):
                classification = MarkerClassification("marker_term_reference", "contextual")
            elif _inside_html_comment(text, hit):
                classification = MarkerClassification(
                    "document_comment_marker",
                    "review",
                    contract_source,
                )
            elif UNCHECKED_TASK_PATTERN.search(hit.line_text[: hit.column]):
                classification = MarkerClassification(
                    "unchecked_task_marker",
                    "review",
                    contract_source,
                )
            elif contract_source or role in {"skill", "agent_instruction", "ci"}:
                classification = MarkerClassification(
                    "contract_prose_marker",
                    "review",
                    True,
                )
            elif operational_source:
                classification = MarkerClassification(
                    "operational_state_marker",
                    "review",
                )
            else:
                classification = MarkerClassification("documentation_marker", "contextual")
            classifications[hit] = classification
        return classifications

    if suffix == ".py":
        lexical = _python_contexts(text, hits)
    elif suffix in JAVASCRIPT_SUFFIXES:
        lexical = _generic_code_contexts(
            text,
            hits,
            slash_comments=True,
            hash_comments=False,
        )
    elif suffix == ".sh":
        lexical = _generic_code_contexts(
            text,
            hits,
            slash_comments=False,
            hash_comments=True,
        )
    else:
        lexical = {hit: "code" for hit in hits}

    if suffix in SOURCE_SUFFIXES:
        classifications = {}
        for hit in hits:
            context = lexical[hit]
            if context == "comment":
                classifications[hit] = MarkerClassification(
                    "source_comment_marker",
                    "review",
                    role == "ci",
                )
            elif context == "string":
                classifications[hit] = MarkerClassification(
                    "string_literal_marker",
                    "contextual",
                )
            else:
                classifications[hit] = MarkerClassification(
                    "source_token_marker",
                    "contextual",
                )
        return classifications

    if suffix in CONFIG_SUFFIXES or role == "config":
        return {
            hit: MarkerClassification("config_value_marker", "contextual")
            for hit in hits
        }
    return {
        hit: MarkerClassification("unclassified_marker", "contextual")
        for hit in hits
    }
