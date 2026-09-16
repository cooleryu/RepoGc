from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any


LIVENESS_DECLARATION_KINDS = (
    "retention",
    "dynamic_consumer",
    "external_system_consumer",
    "runtime_access",
)


@dataclass(frozen=True, order=True)
class LivenessDeclaration:
    path: str
    kind: str
    source: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "kind": self.kind,
            "source": self.source,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class Config:
    include_suffixes: tuple[str, ...] = (
        ".md",
        ".txt",
        ".py",
        ".toml",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".sh",
    )
    orphan_suffixes: tuple[str, ...] = (".md",)
    duplicate_suffixes: tuple[str, ...] = (".md", ".txt")
    exclude_dirs: tuple[str, ...] = (
        ".git",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "vendor",
        ".tmp",
        ".brb",
        "docs/gc_reports",
        "reference/gc_reports",
    )
    exclude_globs: tuple[str, ...] = ("**/*.egg-info/**",)
    root_files: tuple[str, ...] = (
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
    )
    max_file_bytes: int = 1_000_000
    duplicate_threshold: float = 0.96
    duplicate_min_chars: int = 120
    use_git: bool = True
    marker_tokens: tuple[str, ...] = (
        "TODO",
        "FIXME",
        "XXX",
        "NOT_IMPLEMENTED",
        "未实现",
        "待实现",
    )
    graph_root_globs: tuple[str, ...] = (
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".agents/skills/**/SKILL.md",
    )
    instruction_globs: tuple[str, ...] = (
        "AGENTS.md",
        "**/AGENTS.md",
        "CLAUDE.md",
        "**/CLAUDE.md",
        "**/SKILL.md",
    )
    contract_globs: tuple[str, ...] = ("**/SKILL.md",)
    test_globs: tuple[str, ...] = ("test/**", "tests/**", "**/fixtures/**")
    generated_globs: tuple[str, ...] = (
        "docs/gc_reports/**",
        "reference/gc_reports/**",
        "**/runs/**",
    )
    ci_globs: tuple[str, ...] = (".github/workflows/**", ".gitlab-ci.yml")
    config_globs: tuple[str, ...] = (
        "package.json",
        "pyproject.toml",
        "Cargo.toml",
        "repogc.toml",
    )
    config_reference_keys: tuple[str, ...] = (
        "main",
        "module",
        "browser",
        "types",
        "bin",
        "exports",
        "scripts",
    )
    state_reference_keys: tuple[str, ...] = ("artifacts",)
    liveness_declarations: tuple[LivenessDeclaration, ...] = ()
    markdown_report: str = "docs/gc_reports/latest.md"
    json_report: str = "docs/gc_reports/latest.json"
    baseline: str = "reference/gc_reports/baseline.json"

    def digest(self) -> str:
        payload = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _tuple_of_strings(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be an array of strings")
    return tuple(value)


def _liveness_declarations(value: Any) -> tuple[LivenessDeclaration, ...]:
    if not isinstance(value, list):
        raise ValueError("liveness.declarations must be an array of tables")
    declarations: set[LivenessDeclaration] = set()
    for index, item in enumerate(value):
        name = f"liveness.declarations[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{name} must be a table")
        required = ("path", "kind", "source", "reason")
        if any(not isinstance(item.get(key), str) or not item[key].strip() for key in required):
            raise ValueError(f"{name} requires non-empty path, kind, source, and reason strings")
        raw_path = item["path"].strip().replace("\\", "/")
        candidate = PurePosixPath(raw_path)
        windows_absolute = (
            len(raw_path) >= 3
            and raw_path[0].isalpha()
            and raw_path[1:3] == ":/"
        )
        if (
            candidate.is_absolute()
            or windows_absolute
            or ".." in candidate.parts
            or candidate.as_posix() in {"", "."}
        ):
            raise ValueError(f"{name}.path must be a repository-relative path without '..'")
        kind = item["kind"].strip()
        if kind not in LIVENESS_DECLARATION_KINDS:
            allowed = ", ".join(LIVENESS_DECLARATION_KINDS)
            raise ValueError(f"{name}.kind must be one of: {allowed}")
        declarations.add(
            LivenessDeclaration(
                path=candidate.as_posix(),
                kind=kind,
                source=item["source"].strip(),
                reason=item["reason"].strip(),
            )
        )
    return tuple(sorted(declarations))


def load_config(root: Path, path: Path | None = None) -> tuple[Config, Path | None]:
    candidate = path or (root / "repogc.toml")
    if not candidate.exists():
        if path is not None:
            raise FileNotFoundError(f"Config file not found: {candidate}")
        return Config(), None

    with candidate.open("rb") as handle:
        data = tomllib.load(handle)

    scan = data.get("scan", {})
    markers = data.get("markers", {})
    reports = data.get("reports", {})
    graph = data.get("graph", {})
    liveness = data.get("liveness", {})
    if not all(
        isinstance(section, dict)
        for section in (scan, markers, graph, liveness, reports)
    ):
        raise ValueError("scan, markers, graph, liveness, and reports must be TOML tables")

    defaults = Config()
    config = Config(
        include_suffixes=_tuple_of_strings(
            scan.get("include_suffixes", list(defaults.include_suffixes)), "scan.include_suffixes"
        ),
        orphan_suffixes=_tuple_of_strings(
            scan.get("orphan_suffixes", list(defaults.orphan_suffixes)), "scan.orphan_suffixes"
        ),
        duplicate_suffixes=_tuple_of_strings(
            scan.get("duplicate_suffixes", list(defaults.duplicate_suffixes)),
            "scan.duplicate_suffixes",
        ),
        exclude_dirs=_tuple_of_strings(
            scan.get("exclude_dirs", list(defaults.exclude_dirs)), "scan.exclude_dirs"
        ),
        exclude_globs=_tuple_of_strings(
            scan.get("exclude_globs", list(defaults.exclude_globs)), "scan.exclude_globs"
        ),
        root_files=_tuple_of_strings(scan.get("root_files", list(defaults.root_files)), "scan.root_files"),
        max_file_bytes=int(scan.get("max_file_bytes", defaults.max_file_bytes)),
        duplicate_threshold=float(scan.get("duplicate_threshold", defaults.duplicate_threshold)),
        duplicate_min_chars=int(scan.get("duplicate_min_chars", defaults.duplicate_min_chars)),
        use_git=bool(scan.get("use_git", defaults.use_git)),
        marker_tokens=_tuple_of_strings(
            markers.get("tokens", list(defaults.marker_tokens)), "markers.tokens"
        ),
        graph_root_globs=_tuple_of_strings(
            graph.get("root_globs", list(defaults.graph_root_globs)), "graph.root_globs"
        ),
        instruction_globs=_tuple_of_strings(
            graph.get("instruction_globs", list(defaults.instruction_globs)),
            "graph.instruction_globs",
        ),
        contract_globs=_tuple_of_strings(
            graph.get("contract_globs", list(defaults.contract_globs)), "graph.contract_globs"
        ),
        test_globs=_tuple_of_strings(
            graph.get("test_globs", list(defaults.test_globs)), "graph.test_globs"
        ),
        generated_globs=_tuple_of_strings(
            graph.get("generated_globs", list(defaults.generated_globs)),
            "graph.generated_globs",
        ),
        ci_globs=_tuple_of_strings(
            graph.get("ci_globs", list(defaults.ci_globs)), "graph.ci_globs"
        ),
        config_globs=_tuple_of_strings(
            graph.get("config_globs", list(defaults.config_globs)), "graph.config_globs"
        ),
        config_reference_keys=_tuple_of_strings(
            graph.get("config_reference_keys", list(defaults.config_reference_keys)),
            "graph.config_reference_keys",
        ),
        state_reference_keys=_tuple_of_strings(
            graph.get("state_reference_keys", list(defaults.state_reference_keys)),
            "graph.state_reference_keys",
        ),
        liveness_declarations=_liveness_declarations(
            liveness.get("declarations", [])
        ),
        markdown_report=str(reports.get("markdown", defaults.markdown_report)),
        json_report=str(reports.get("json", defaults.json_report)),
        baseline=str(reports.get("baseline", defaults.baseline)),
    )
    if config.max_file_bytes <= 0:
        raise ValueError("scan.max_file_bytes must be positive")
    if not 0.0 <= config.duplicate_threshold <= 1.0:
        raise ValueError("scan.duplicate_threshold must be between 0 and 1")
    if config.duplicate_min_chars < 0:
        raise ValueError("scan.duplicate_min_chars cannot be negative")
    return config, candidate
