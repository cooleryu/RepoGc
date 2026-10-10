from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Reference:
    source: str
    target: str
    raw: str
    line: int
    column: int = 0


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    kind: str
    syntax: str
    evidence: str
    line: int
    strength: str
    traversable: bool
    contract_sensitive: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "syntax": self.syntax,
            "evidence": self.evidence,
            "line": self.line,
            "strength": self.strength,
            "traversable": self.traversable,
            "contract_sensitive": self.contract_sensitive,
        }


@dataclass(frozen=True)
class Artifact:
    path: str
    role: str
    exists: bool
    root: bool
    scanned: bool
    reachable: bool
    reachable_from: str | None = None
    evidence_path: tuple[str, ...] = ()
    incoming_edge_kinds: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "role": self.role,
            "exists": self.exists,
            "root": self.root,
            "scanned": self.scanned,
            "reachable": self.reachable,
            "reachable_from": self.reachable_from,
            "evidence_path": list(self.evidence_path),
            "incoming_edge_kinds": list(self.incoming_edge_kinds),
        }


@dataclass(frozen=True)
class Finding:
    id: str
    category: str
    source: str
    target: str | None
    evidence: str
    rule: str
    line: int | None = None
    referenced_by: tuple[str, ...] = ()
    contract_sensitive: bool = False
    evidence_kind: str = "mechanical_observation"
    evidence_strength: str = "candidate"
    git_last_touch: dict[str, str] | None = None
    known_limitations: str = "Static scan surface only; dynamic and external consumers may be unobserved."
    human_review: str = "Review repository semantics and all human, machine, contract, and process consumers."

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "source": self.source,
            "target": self.target,
            "evidence": self.evidence,
            "rule": self.rule,
            "line": self.line,
            "referenced_by": list(self.referenced_by),
            "contract_sensitive": self.contract_sensitive,
            "evidence_kind": self.evidence_kind,
            "evidence_strength": self.evidence_strength,
            "git_last_touch": self.git_last_touch,
            "known_limitations": self.known_limitations,
            "human_review": self.human_review,
            "ai_annotation_status": "not_run",
        }


@dataclass(frozen=True)
class SelfCheckResult:
    ok: bool
    checks: tuple[str, ...]
    failures: tuple[str, ...] = ()


@dataclass
class ScanResult:
    reliability: str
    reliability_reasons: list[str]
    findings: list[Finding]
    scanned_files: int
    skipped_files: list[dict[str, str]]
    repository: dict[str, str | bool | None]
    scanner_hash: str
    config_hash: str
    generated_at: str
    self_check: SelfCheckResult
    trend: dict[str, Any] = field(default_factory=dict)
    scan_integrity: str = "PASS"
    coverage: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    liveness_declarations: list[dict[str, str]] = field(default_factory=list)
    source_contents: dict[str, str] = field(default_factory=dict, repr=False)

    def category_counts(self) -> dict[str, int]:
        categories = (
            "broken_reference",
            "placeholder_text",
            "orphan_candidate",
            "unimplemented_marker",
            "duplicate_candidate",
            "unreachable_candidate",
        )
        return {
            category: sum(1 for finding in self.findings if finding.category == category)
            for category in categories
        }
