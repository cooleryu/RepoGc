from __future__ import annotations

import difflib
import hashlib
import os
import posixpath
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from repogc.config import Config
from repogc.git_info import last_touch, repository_info
from repogc.graph import build_evidence_graph, coverage_summary, matches_any
from repogc.marker_context import MarkerHit, classify_marker_hits
from repogc.models import Edge, Finding, Reference, ScanResult, SelfCheckResult


PATH_PATTERN = re.compile(
    r"(?<![\w@./-])"
    r"(?P<path>(?:(?:\.\.?/)?(?:[\w@+.-]+/)*[\w@+.-]+\."
    r"(?:jsonl|json|yaml|yml|toml|markdown|md|python|py|shell|sh|text|txt|"
    r"mjs|cjs|jsx|tsx|js|ts)))"
    r"(?![\w-]|\.[\w])",
    re.IGNORECASE | re.UNICODE,
)
NEGATION_PATTERN = re.compile(
    r"(?:没有|不存在|无需|不使用|without|no|not)\s*[`'\"]?\s*$",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def normalize_relative_path(value: str) -> str:
    normalized = posixpath.normpath(value.replace("\\", "/"))
    if normalized == ".":
        return ""
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def stable_id(source: str, evidence: str) -> str:
    normalized_source = normalize_relative_path(source)
    normalized_evidence = normalize_text(evidence)[:40]
    digest = hashlib.sha1(
        f"{normalized_source}\0{normalized_evidence}".encode("utf-8")
    ).hexdigest()
    return digest


def scanner_hash() -> str:
    package_dir = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(package_dir.glob("*.py"), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _is_negated(line: str, start: int) -> bool:
    prefix = line[max(0, start - 32) : start]
    return NEGATION_PATTERN.search(prefix) is not None


def _is_url_path(line: str, start: int) -> bool:
    prefix = line[max(0, start - 16) : start]
    return "://" in prefix or prefix.endswith("mailto:")


def _is_markdown_link_label(line: str, start: int, end: int) -> bool:
    opening = line.rfind("[", 0, start)
    closing = line.find("](", end)
    if opening == -1 or closing == -1:
        return False
    return "]" not in line[opening:start]


def _candidate_paths(source: str, raw: str) -> list[str]:
    clean = raw.split("#", 1)[0].split("?", 1)[0].replace("\\", "/")
    source_parent = PurePosixPath(source).parent.as_posix()
    relative = normalize_relative_path(posixpath.join(source_parent, clean))
    rooted = normalize_relative_path(clean)
    if clean.startswith(("./", "../")) or "/" not in clean:
        candidates = [relative, rooted]
    else:
        candidates = [rooted, relative]
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def extract_references(source: str, text: str, known_paths: set[str]) -> list[Reference]:
    references: list[Reference] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in PATH_PATTERN.finditer(line):
            raw = match.group("path")
            if (
                _is_url_path(line, match.start("path"))
                or _is_negated(line, match.start("path"))
                or _is_markdown_link_label(line, match.start("path"), match.end("path"))
            ):
                continue
            candidates = _candidate_paths(source, raw)
            target = next((candidate for candidate in candidates if candidate in known_paths), candidates[0])
            references.append(
                Reference(
                    source=source,
                    target=target,
                    raw=raw,
                    line=line_number,
                    column=match.start("path"),
                )
            )
    return references


def compute_inbound(references: list[Reference], known_paths: set[str]) -> dict[str, set[str]]:
    inbound: dict[str, set[str]] = {path: set() for path in known_paths}
    for reference in references:
        if reference.target in known_paths and reference.target != reference.source:
            inbound[reference.target].add(reference.source)
    return inbound


def _discover_existing_reference_targets(
    root: Path, contents: dict[str, str], scanned_paths: set[str]
) -> set[str]:
    """Add existing targets without widening the content scan surface."""
    existing = set(scanned_paths)
    root_resolved = root.resolve()
    for source, text in contents.items():
        for line in text.splitlines():
            for match in PATH_PATTERN.finditer(line):
                if (
                    _is_url_path(line, match.start("path"))
                    or _is_negated(line, match.start("path"))
                    or _is_markdown_link_label(line, match.start("path"), match.end("path"))
                ):
                    continue
                for candidate in _candidate_paths(source, match.group("path")):
                    if candidate == ".." or candidate.startswith("../"):
                        continue
                    full_path = (root_resolved / candidate).resolve()
                    if root_resolved not in full_path.parents or full_path.is_symlink():
                        continue
                    if full_path.is_file():
                        existing.add(candidate)
                        break
    return existing


def _is_excluded(relative: PurePosixPath, exclusions: tuple[str, ...]) -> bool:
    relative_text = relative.as_posix()
    for exclusion in exclusions:
        clean = exclusion.strip("/")
        if not clean:
            continue
        if "/" in clean:
            if relative_text == clean or relative_text.startswith(f"{clean}/"):
                return True
        elif clean in relative.parts:
            return True
    return False


def collect_text_files(
    root: Path, config: Config
) -> tuple[dict[str, str], list[dict[str, str]]]:
    contents: dict[str, str] = {}
    skipped: list[dict[str, str]] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        relative_directory = PurePosixPath(directory_path.relative_to(root).as_posix())
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            candidate = relative_directory / dirname
            full_candidate = directory_path / dirname
            if _is_excluded(candidate, config.exclude_dirs) or full_candidate.is_symlink():
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            path = directory_path / filename
            relative = path.relative_to(root).as_posix()
            relative_path = PurePosixPath(relative)
            if _is_excluded(relative_path, config.exclude_dirs):
                continue
            if matches_any(relative, config.exclude_globs):
                continue
            if path.is_symlink() or path.suffix.lower() not in config.include_suffixes:
                continue
            try:
                size = path.stat().st_size
                if size > config.max_file_bytes:
                    skipped.append({"path": relative, "reason": "file exceeds max_file_bytes"})
                    continue
                data = path.read_bytes()
                if b"\x00" in data:
                    skipped.append({"path": relative, "reason": "binary content detected"})
                    continue
                contents[relative] = data.decode("utf-8")
            except (OSError, UnicodeDecodeError) as error:
                skipped.append({"path": relative, "reason": f"read failed: {type(error).__name__}"})
    return dict(sorted(contents.items())), sorted(skipped, key=lambda item: item["path"])


def _normalized_document(text: str) -> str:
    lines = [normalize_text(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).casefold()


def _sequence_ratio_upper_bound(left: str, right: str) -> float:
    total = len(left) + len(right)
    if total == 0:
        return 1.0
    return (2.0 * min(len(left), len(right))) / total


def _finding(
    category: str,
    source: str,
    target: str | None,
    evidence: str,
    rule: str,
    *,
    line: int | None = None,
    referenced_by: tuple[str, ...] = (),
    contract_sensitive: bool = False,
    evidence_kind: str = "mechanical_observation",
    evidence_strength: str = "candidate",
    git_context: dict[str, str] | None = None,
    known_limitations: str | None = None,
    human_review: str | None = None,
) -> Finding:
    return Finding(
        id=stable_id(source, evidence),
        category=category,
        source=source,
        target=target,
        evidence=evidence,
        rule=rule,
        line=line,
        referenced_by=referenced_by,
        contract_sensitive=contract_sensitive,
        evidence_kind=evidence_kind,
        evidence_strength=evidence_strength,
        git_last_touch=git_context,
        known_limitations=known_limitations
        or "Static scan surface only; dynamic and external consumers may be unobserved.",
        human_review=human_review
        or "Review repository semantics and all human, machine, contract, and process consumers.",
    )


def scan_repository(root: Path, config: Config, self_check: SelfCheckResult) -> ScanResult:
    root = root.resolve()
    contents, skipped = collect_text_files(root, config)
    scanned_paths = set(contents)
    known_paths = _discover_existing_reference_targets(root, contents, scanned_paths)
    references = [
        reference
        for source, text in contents.items()
        for reference in extract_references(source, text, known_paths)
    ]
    inbound = compute_inbound(references, scanned_paths)
    artifacts, edges = build_evidence_graph(contents, references, known_paths, config)
    edges_by_target: dict[tuple[str, str], list[Edge]] = {}
    for edge in edges:
        edges_by_target.setdefault((edge.source, edge.target), []).append(edge)
    repository, git_problem = repository_info(root, config.use_git)
    touch_cache: dict[str, dict[str, str] | None] = {}

    def git_context(source: str) -> dict[str, str] | None:
        if source not in touch_cache:
            touch_cache[source] = last_touch(root, source, config.use_git)
        return touch_cache[source]

    findings_by_id: dict[str, Finding] = {}

    for reference in references:
        if reference.target in known_paths:
            continue
        reference_edges = edges_by_target[(reference.source, reference.target)]
        representative_edge = min(
            reference_edges,
            key=lambda edge: (
                edge.strength != "strong",
                not edge.contract_sensitive,
                edge.kind,
            ),
        )
        evidence = f"unresolved path: {reference.raw}"
        finding = _finding(
            "broken_reference",
            reference.source,
            reference.target,
            evidence,
            "path_reference_target_missing",
            line=reference.line,
            contract_sensitive=any(edge.contract_sensitive for edge in reference_edges),
            evidence_kind=representative_edge.kind,
            evidence_strength=representative_edge.strength,
            git_context=git_context(reference.source),
            known_limitations=(
                "The path may be generated, external, intentionally illustrative, or outside the configured scan surface."
            ),
            human_review="Confirm the intended resolution context before changing the reference.",
        )
        findings_by_id.setdefault(finding.id, finding)

    root_files = {normalize_relative_path(path) for path in config.root_files}
    root_files.update(artifact.path for artifact in artifacts if artifact.root)
    artifacts_by_path = {artifact.path: artifact for artifact in artifacts}
    for source in sorted(scanned_paths):
        if (
            Path(source).suffix.lower() not in config.orphan_suffixes
            or source in root_files
            or artifacts_by_path[source].role in {"test", "generated"}
        ):
            continue
        incoming = tuple(sorted(inbound.get(source, set())))
        if incoming:
            continue
        evidence = "no inbound reference observed in configured scan surface"
        finding = _finding(
            "orphan_candidate",
            source,
            None,
            evidence,
            "markdown_inbound_reference_absent",
            referenced_by=incoming,
            contract_sensitive=matches_any(source, config.contract_globs),
            evidence_kind="inbound_absence",
            evidence_strength="candidate",
            git_context=git_context(source),
            known_limitations=(
                "Human navigation, external systems, dynamic access, contracts, and unconfigured roots may be unobserved."
            ),
            human_review="Check all liveness dimensions; this candidate is not a deletion recommendation.",
        )
        findings_by_id.setdefault(finding.id, finding)

    marker_parts = []
    for token in sorted(config.marker_tokens, key=len, reverse=True):
        escaped = re.escape(token)
        if re.fullmatch(r"[A-Za-z0-9_]+", token):
            escaped = rf"(?<![\w-]){escaped}(?![\w-])"
        marker_parts.append(escaped)
    marker_pattern = re.compile("|".join(marker_parts)) if marker_parts else None
    for source, text in contents.items():
        if marker_pattern is None:
            break
        hits: list[MarkerHit] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in marker_pattern.finditer(line):
                hits.append(
                    MarkerHit(
                        line=line_number,
                        column=match.start(),
                        line_text=line,
                        token=match.group(0),
                    )
                )
        role = artifacts_by_path[source].role
        classifications = classify_marker_hits(
            source,
            text,
            role,
            hits,
            contract_source=(
                matches_any(source, config.contract_globs)
                or role in {"skill", "agent_instruction", "ci"}
            ),
            operational_source=(
                role == "harness_state" and artifacts_by_path[source].root
            ),
        )
        hits_by_line: dict[int, list[MarkerHit]] = {}
        for hit in hits:
            hits_by_line.setdefault(hit.line, []).append(hit)
        for line_number, line_hits in hits_by_line.items():
            representative_hit = min(
                line_hits,
                key=lambda hit: (
                    classifications[hit].strength != "review",
                    not classifications[hit].contract_sensitive,
                    classifications[hit].kind,
                    hit.column,
                ),
            )
            classification = classifications[representative_hit]
            line = representative_hit.line_text
            evidence = normalize_text(line)
            finding = _finding(
                "unimplemented_marker",
                source,
                None,
                evidence,
                "configured_unimplemented_marker",
                line=line_number,
                contract_sensitive=any(
                    classifications[hit].contract_sensitive for hit in line_hits
                ),
                evidence_kind=classification.kind,
                evidence_strength=classification.strength,
                git_context=git_context(source),
                known_limitations=(
                    "Marker context is lexical; macro expansion, generated source maps, and business intent remain unobserved."
                ),
                human_review=(
                    "Confirm whether this review-tier marker is an active commitment."
                    if classification.strength == "review"
                    else "Contextual marker only; do not treat it as an active task without additional evidence."
                ),
            )
            findings_by_id.setdefault(finding.id, finding)

    incoming_sources: dict[str, set[str]] = {}
    for edge in edges:
        incoming_sources.setdefault(edge.target, set()).add(edge.source)
    unreachable_roles = {"document", "skill", "agent_instruction", "harness_state"}
    configured_root_count = sum(1 for artifact in artifacts if artifact.root)
    for artifact in artifacts:
        if (
            not artifact.exists
            or not artifact.scanned
            or artifact.root
            or artifact.reachable
            or artifact.role not in unreachable_roles
        ):
            continue
        evidence = "no traversable evidence path from any configured root"
        finding = _finding(
            "unreachable_candidate",
            artifact.path,
            None,
            evidence,
            "configured_root_typed_edge_reachability_absent",
            referenced_by=tuple(sorted(incoming_sources.get(artifact.path, set()))),
            contract_sensitive=artifact.role in {"skill", "agent_instruction", "harness_state"},
            evidence_kind="reachability_absence",
            evidence_strength="candidate",
            git_context=git_context(artifact.path),
            known_limitations=(
                "Only configured roots and supported static edge types participate; dynamic and external consumers remain unknown."
            ),
            human_review=(
                f"Review root configuration and unsupported consumers; {configured_root_count} root(s) were configured."
            ),
        )
        findings_by_id.setdefault(finding.id, finding)

    duplicate_documents = [
        (source, _normalized_document(text))
        for source, text in contents.items()
        if Path(source).suffix.lower() in config.duplicate_suffixes
        and len(_normalized_document(text)) >= config.duplicate_min_chars
    ]
    for index, (source, normalized_source) in enumerate(duplicate_documents):
        for target, normalized_target in duplicate_documents[index + 1 :]:
            if (
                _sequence_ratio_upper_bound(normalized_source, normalized_target)
                < config.duplicate_threshold
            ):
                continue
            similarity = difflib.SequenceMatcher(None, normalized_source, normalized_target).ratio()
            if similarity < config.duplicate_threshold:
                continue
            evidence = f"target={target}; normalized similarity={similarity:.3f}"
            finding = _finding(
                "duplicate_candidate",
                source,
                target,
                evidence,
                "normalized_document_similarity_threshold",
                evidence_kind="document_similarity",
                evidence_strength="candidate",
                git_context=git_context(source),
                known_limitations="Similarity does not establish equivalent purpose, authority, or safe consolidation.",
                human_review="Compare authority, consumers, history, and semantic differences before any action.",
            )
            findings_by_id.setdefault(finding.id, finding)

    reasons: list[str] = []
    if not self_check.ok:
        reliability = "UNRELIABLE"
        reasons.extend(self_check.failures)
    else:
        if skipped:
            reasons.append(f"{len(skipped)} configured file(s) could not be scanned completely.")
        if git_problem:
            reasons.append(git_problem)
        reliability = "PARTIAL" if reasons else "RELIABLE"

    findings = sorted(
        findings_by_id.values(),
        key=lambda item: (item.category, item.source, item.target or "", item.evidence, item.id),
    )
    scan_integrity = {
        "RELIABLE": "PASS",
        "PARTIAL": "PARTIAL",
        "UNRELIABLE": "FAIL",
    }[reliability]
    return ScanResult(
        reliability=reliability,
        reliability_reasons=reasons,
        findings=findings,
        scanned_files=len(contents),
        skipped_files=skipped,
        repository=repository,
        scanner_hash=scanner_hash(),
        config_hash=config.digest(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        self_check=self_check,
        scan_integrity=scan_integrity,
        coverage=coverage_summary(config),
        artifacts=artifacts,
        edges=edges,
        source_contents=contents,
        liveness_declarations=[
            declaration.to_dict() for declaration in config.liveness_declarations
        ],
    )
