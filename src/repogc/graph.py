from __future__ import annotations

import fnmatch
import hashlib
import posixpath
import re
import unicodedata
from collections import deque
from dataclasses import replace
from pathlib import Path

from repogc.config import Config
from repogc.models import Artifact, Edge, Reference


MARKDOWN_LINK_PATTERN = re.compile(
    r"\[[^\]]*\]\(\s*<?(?P<target>[^)\s>]+)>?(?:\s+['\"][^)]*['\"])?\s*\)"
)
SOURCE_IMPORT_PATTERN = re.compile(
    r"(?:\bfrom\s+|\bimport\s+|\bimport\s*\(|\brequire\s*\()"
    r"\s*['\"](?P<target>[^'\"]+)['\"]"
)
CONTRACT_CUE_PATTERN = re.compile(
    r"\b(?:must|required|deliverable|artifact|input|output|read|write|consume|check|verify)\b"
    r"|必须|应当|需要|交付|产出|读取|写入|消费|检查|验证",
    re.IGNORECASE,
)
JSON_KEY_PATTERN = re.compile(r'"(?P<key>[^"\\]+)"\s*:')


def matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatchcase(path, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:]):
            return True
    return False


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _edge_id(source: str, target: str, kind: str, evidence: str) -> str:
    payload = "\0".join(
        (
            posixpath.normpath(source.replace("\\", "/")),
            posixpath.normpath(target.replace("\\", "/")),
            kind,
            _normalized_text(evidence)[:80],
        )
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def artifact_role(path: str, config: Config) -> str:
    if matches_any(path, config.generated_globs):
        return "generated"
    if matches_any(path, config.test_globs):
        return "test"
    if Path(path).name == "SKILL.md":
        return "skill"
    if matches_any(path, config.instruction_globs):
        return "agent_instruction"
    if matches_any(path, config.ci_globs):
        return "ci"
    if matches_any(path, config.config_globs):
        return "config"
    if path.startswith(".harness/"):
        return "harness_state"
    suffix = Path(path).suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        return "document"
    if suffix in {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh"}:
        return "source"
    return "artifact"


def _fenced_markdown_lines(text: str) -> set[int]:
    fenced: set[int] = set()
    fence_marker: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            marker = "```"
        elif stripped.startswith("~~~"):
            marker = "~~~"
        else:
            marker = None
        if fence_marker is not None:
            fenced.add(line_number)
            if marker == fence_marker:
                fence_marker = None
        elif marker is not None:
            fence_marker = marker
            fenced.add(line_number)
    return fenced


def _json_container_delta(value: str) -> int:
    depth = 0
    in_string = False
    escaped = False
    for character in value:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
    return depth


def _structured_json_syntaxes(
    source: str,
    text: str,
    references: list[Reference],
    config: Config,
) -> dict[tuple[int, str, int], str]:
    if Path(source).suffix.lower() not in {".json", ".jsonl"}:
        return {}
    references_by_line: dict[int, list[Reference]] = {}
    for reference in references:
        references_by_line.setdefault(reference.line, []).append(reference)
    if not references_by_line:
        return {}

    key_syntax: dict[str, str] = {}
    if matches_any(source, config.config_globs):
        key_syntax.update((key, "config_entry") for key in config.config_reference_keys)
    if source.startswith(".harness/"):
        key_syntax.update((key, "state_artifact") for key in config.state_reference_keys)
    if not key_syntax:
        return {}

    syntaxes: dict[tuple[int, str, int], str] = {}
    active_blocks: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped:
            while active_blocks and indent <= active_blocks[-1][0] and stripped[0] in "]}":
                active_blocks.pop()

        inherited_syntax = active_blocks[-1][1] if active_blocks else None
        key_matches = list(JSON_KEY_PATTERN.finditer(line))
        for reference in references_by_line.get(line_number, []):
            preceding = [match for match in key_matches if match.start() < reference.column]
            syntax = None
            if preceding:
                syntax = key_syntax.get(preceding[-1].group("key"))
            if syntax is None and inherited_syntax is not None:
                syntax = inherited_syntax
            if syntax is None:
                for match in reversed(preceding[:-1]):
                    candidate = key_syntax.get(match.group("key"))
                    if candidate is None:
                        continue
                    if _json_container_delta(line[match.end() : reference.column]) > 0:
                        syntax = candidate
                        break
            if syntax is not None:
                syntaxes[(line_number, reference.raw, reference.column)] = syntax

        for match in key_matches:
            syntax = key_syntax.get(match.group("key"))
            if syntax is None:
                continue
            tail = line[match.end() :]
            if _json_container_delta(tail) > 0:
                active_blocks.append((indent, syntax))
    return syntaxes


def _reference_syntax(
    source: str,
    line: str,
    raw: str,
    line_number: int,
    fenced_lines: set[int],
    structured_syntaxes: dict[tuple[int, str, int], str],
    column: int,
) -> str:
    if line_number in fenced_lines:
        return "fenced_code"
    structured = structured_syntaxes.get((line_number, raw, column))
    if structured is not None:
        return structured
    if Path(source).suffix.lower() in {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}:
        if any(raw in match.group("target") for match in SOURCE_IMPORT_PATTERN.finditer(line)):
            return "source_import"
    if any(raw in match.group("target") for match in MARKDOWN_LINK_PATTERN.finditer(line)):
        return "markdown_link"
    return "path_token"


def _edge_kind(
    source: str,
    source_role: str,
    syntax: str,
    line: str,
    config: Config,
) -> tuple[str, str, bool, bool]:
    if source_role == "test":
        return "test_reference", "contextual", False, False
    if syntax == "fenced_code":
        return "example_reference", "contextual", False, False
    if source_role == "ci":
        return "ci_reference", "strong", True, True
    if syntax == "config_entry":
        return "config_reference", "strong", True, False
    if syntax == "state_artifact":
        return "state_reference", "strong", True, False
    if matches_any(source, config.contract_globs) and CONTRACT_CUE_PATTERN.search(line):
        return "declared_contract_reference", "strong", True, True
    if source_role in {"skill", "agent_instruction"}:
        return "instruction_reference", "strong", True, True
    if syntax == "source_import":
        return "source_import", "strong", True, False
    if syntax == "markdown_link":
        return "markdown_link", "strong", True, False
    return "path_mention", "contextual", False, False


def coverage_summary(config: Config | None = None) -> dict[str, object]:
    declaration_kinds = {
        declaration.kind
        for declaration in (() if config is None else config.liveness_declarations)
    }

    def declared_or_unobserved(kind: str) -> str:
        return "DECLARATIONS_ONLY" if kind in declaration_kinds else "NOT_OBSERVED"

    return {
        "status": "LIMITED",
        "meaning": "Configured static surfaces were inspected; semantic completeness is not claimed.",
        "surfaces": [
            {"name": "path_tokens", "status": "CHECKED"},
            {"name": "markdown_links", "status": "CHECKED"},
            {"name": "explicit_extension_source_imports", "status": "CHECKED"},
            {"name": "declared_instruction_contracts", "status": "CHECKED"},
            {"name": "configured_ci_files", "status": "CHECKED"},
            {"name": "configured_json_reference_fields", "status": "CHECKED"},
            {"name": "fenced_code_context", "status": "CHECKED"},
            {"name": "python_marker_token_context", "status": "CHECKED"},
            {"name": "js_ts_shell_marker_lexical_context", "status": "CHECKED"},
            {"name": "markdown_marker_context", "status": "CHECKED"},
            {"name": "human_liveness_declarations", "status": "CHECKED"},
            {
                "name": "dynamic_consumers",
                "status": declared_or_unobserved("dynamic_consumer"),
            },
            {
                "name": "external_system_consumers",
                "status": declared_or_unobserved("external_system_consumer"),
            },
            {
                "name": "runtime_access_events",
                "status": declared_or_unobserved("runtime_access"),
            },
            {"name": "business_meaning", "status": "NOT_INFERRED"},
        ],
    }


def build_evidence_graph(
    contents: dict[str, str],
    references: list[Reference],
    existing_paths: set[str],
    config: Config,
) -> tuple[list[Artifact], list[Edge]]:
    graph_paths = existing_paths | {
        path
        for reference in references
        for path in (reference.source, reference.target)
    }
    artifacts_by_path = {
        path: Artifact(
            path=path,
            role=artifact_role(path, config),
            exists=path in existing_paths,
            root=path in existing_paths and matches_any(path, config.graph_root_globs),
            scanned=path in contents,
            reachable=False,
        )
        for path in sorted(graph_paths)
    }

    references_by_source: dict[str, list[Reference]] = {}
    for reference in references:
        references_by_source.setdefault(reference.source, []).append(reference)
    fenced_by_source = {
        source: _fenced_markdown_lines(text)
        for source, text in contents.items()
        if Path(source).suffix.lower() in {".md", ".markdown"}
    }
    structured_by_source = {
        source: _structured_json_syntaxes(
            source,
            contents[source],
            source_references,
            config,
        )
        for source, source_references in references_by_source.items()
    }

    edges_by_id: dict[str, Edge] = {}
    for reference in references:
        line = contents[reference.source].splitlines()[reference.line - 1]
        source_role = artifacts_by_path[reference.source].role
        syntax = _reference_syntax(
            reference.source,
            line,
            reference.raw,
            reference.line,
            fenced_by_source.get(reference.source, set()),
            structured_by_source.get(reference.source, {}),
            reference.column,
        )
        kind, strength, traversable, contract_sensitive = _edge_kind(
            reference.source,
            source_role,
            syntax,
            line,
            config,
        )
        evidence = _normalized_text(line)
        edge = Edge(
            id=_edge_id(reference.source, reference.target, kind, evidence),
            source=reference.source,
            target=reference.target,
            kind=kind,
            syntax=syntax,
            evidence=evidence,
            line=reference.line,
            strength=strength,
            traversable=traversable,
            contract_sensitive=contract_sensitive,
        )
        edges_by_id.setdefault(edge.id, edge)

    edges = sorted(
        edges_by_id.values(),
        key=lambda item: (item.source, item.target, item.kind, item.evidence, item.id),
    )
    incoming: dict[str, set[str]] = {path: set() for path in artifacts_by_path}
    adjacency: dict[str, list[Edge]] = {path: [] for path in artifacts_by_path}
    for edge in edges:
        incoming[edge.target].add(edge.kind)
        if edge.traversable and artifacts_by_path[edge.target].exists:
            adjacency[edge.source].append(edge)
    for edge_list in adjacency.values():
        edge_list.sort(key=lambda item: (item.target, item.kind, item.id))

    paths: dict[str, tuple[str, ...]] = {}
    roots: dict[str, str] = {}
    queue: deque[str] = deque()
    for path, artifact in artifacts_by_path.items():
        if artifact.root:
            paths[path] = (path,)
            roots[path] = path
            queue.append(path)
    while queue:
        source = queue.popleft()
        for edge in adjacency[source]:
            if edge.target in paths:
                continue
            paths[edge.target] = paths[source] + (edge.target,)
            roots[edge.target] = roots[source]
            queue.append(edge.target)

    artifacts = [
        replace(
            artifact,
            reachable=path in paths,
            reachable_from=roots.get(path),
            evidence_path=paths.get(path, ()),
            incoming_edge_kinds=tuple(sorted(incoming[path])),
        )
        for path, artifact in artifacts_by_path.items()
    ]
    return artifacts, edges
