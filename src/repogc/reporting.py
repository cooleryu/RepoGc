from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repogc import REPORT_SCHEMA_VERSION, __version__
from repogc.annotations import ANNOTATION_SCHEMA_VERSION
from repogc.liveness import build_liveness_profiles, finding_subject_paths
from repogc.models import ScanResult


def report_payload(result: ScanResult) -> dict[str, Any]:
    existence = {artifact.path: artifact.exists for artifact in result.artifacts}
    roles = {artifact.path: artifact.role for artifact in result.artifacts}
    missing_target_edges = [
        edge for edge in result.edges if not existence.get(edge.target, False)
    ]
    missing_by_kind: dict[str, int] = {}
    for edge in missing_target_edges:
        missing_by_kind[edge.kind] = missing_by_kind.get(edge.kind, 0) + 1
    finding_counts_by_role: dict[str, dict[str, int]] = {}
    contract_sensitive_by_category: dict[str, int] = {}
    finding_counts_by_kind: dict[str, dict[str, int]] = {}
    finding_counts_by_strength: dict[str, dict[str, int]] = {}
    for finding in result.findings:
        role = roles.get(finding.source, "unknown")
        category_roles = finding_counts_by_role.setdefault(finding.category, {})
        category_roles[role] = category_roles.get(role, 0) + 1
        category_kinds = finding_counts_by_kind.setdefault(finding.category, {})
        category_kinds[finding.evidence_kind] = (
            category_kinds.get(finding.evidence_kind, 0) + 1
        )
        category_strengths = finding_counts_by_strength.setdefault(finding.category, {})
        category_strengths[finding.evidence_strength] = (
            category_strengths.get(finding.evidence_strength, 0) + 1
        )
        if finding.contract_sensitive:
            contract_sensitive_by_category[finding.category] = (
                contract_sensitive_by_category.get(finding.category, 0) + 1
            )
    subject_paths = {
        path
        for finding in result.findings
        for path in finding_subject_paths(finding)
    }
    git_last_touch_by_path = {
        finding.source: finding.git_last_touch
        for finding in result.findings
        if finding.git_last_touch is not None
    }
    liveness_profiles = build_liveness_profiles(
        result.artifacts,
        result.edges,
        subject_paths,
        git_last_touch_by_path,
        result.liveness_declarations,
    )
    profiled_paths = {profile["path"] for profile in liveness_profiles}
    matched_declarations = [
        declaration
        for declaration in result.liveness_declarations
        if declaration["path"] in profiled_paths
    ]
    unmatched_declarations = [
        declaration
        for declaration in result.liveness_declarations
        if declaration["path"] not in profiled_paths
    ]
    finding_payloads: list[dict[str, Any]] = []
    for finding in result.findings:
        item = finding.to_dict()
        item["review_subjects"] = list(finding_subject_paths(finding))
        finding_payloads.append(item)
    profiles_with_static_inbound = sum(
        profile["dimensions"]["static_inbound_references"]["status"] == "OBSERVED"
        for profile in liveness_profiles
    )
    profiles_reachable_from_roots = sum(
        profile["dimensions"]["root_reachability"]["status"] == "OBSERVED"
        for profile in liveness_profiles
    )
    return {
        "metadata": {
            "repogc_version": __version__,
            "report_schema_version": REPORT_SCHEMA_VERSION,
            "generated_at": result.generated_at,
            "repository": result.repository,
            "scanner_hash": result.scanner_hash,
            "config_hash": result.config_hash,
            "reliability": result.reliability,
            "reliability_reasons": result.reliability_reasons,
            "scan_integrity": result.scan_integrity,
            "coverage": result.coverage,
            "ai_annotation_status": "not_run",
            "annotation_schema_version": ANNOTATION_SCHEMA_VERSION,
            "scanned_files": result.scanned_files,
            "skipped_files": result.skipped_files,
            "self_check": {
                "ok": result.self_check.ok,
                "checks": list(result.self_check.checks),
                "failures": list(result.self_check.failures),
            },
        },
        "summary": result.category_counts(),
        "evidence_summary": {
            "missing_target_edges": len(missing_target_edges),
            "strong_missing_target_edges": sum(
                1 for edge in missing_target_edges if edge.strength == "strong"
            ),
            "contextual_missing_target_edges": sum(
                1 for edge in missing_target_edges if edge.strength == "contextual"
            ),
            "contract_sensitive_missing_target_edges": sum(
                1 for edge in missing_target_edges if edge.contract_sensitive
            ),
            "missing_target_edges_by_kind": dict(sorted(missing_by_kind.items())),
            "finding_counts_by_role": {
                category: dict(sorted(role_counts.items()))
                for category, role_counts in sorted(finding_counts_by_role.items())
            },
            "contract_sensitive_findings_by_category": dict(
                sorted(contract_sensitive_by_category.items())
            ),
            "finding_counts_by_evidence_kind": {
                category: dict(sorted(kind_counts.items()))
                for category, kind_counts in sorted(finding_counts_by_kind.items())
            },
            "finding_counts_by_evidence_strength": {
                category: dict(sorted(strength_counts.items()))
                for category, strength_counts in sorted(finding_counts_by_strength.items())
            },
            "liveness_profiles": len(liveness_profiles),
            "profiles_with_static_inbound": profiles_with_static_inbound,
            "profiles_reachable_from_roots": profiles_reachable_from_roots,
            "liveness_declarations": len(result.liveness_declarations),
            "matched_liveness_declarations": len(matched_declarations),
            "unmatched_liveness_declarations": len(unmatched_declarations),
            "unobserved_liveness_surfaces": [
                "dynamic_consumers",
                "external_system_consumers",
                "runtime_access",
                "business_meaning",
            ],
        },
        "trend": result.trend,
        "findings": finding_payloads,
        "artifact_liveness": liveness_profiles,
        "liveness_declarations": {
            "count": len(result.liveness_declarations),
            "matched": matched_declarations,
            "unmatched": unmatched_declarations,
            "meaning": (
                "Human-supplied evidence declarations enrich review context; they do not suppress findings or change graph reachability."
            ),
        },
        "artifacts": [artifact.to_dict() for artifact in result.artifacts],
        "edges": [edge.to_dict() for edge in result.edges],
    }


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(payload: dict[str, Any]) -> str:
    metadata = payload["metadata"]
    summary = payload["summary"]
    evidence_summary = payload["evidence_summary"]
    marker_strengths = evidence_summary["finding_counts_by_evidence_strength"].get(
        "unimplemented_marker", {}
    )
    marker_kinds = evidence_summary["finding_counts_by_evidence_kind"].get(
        "unimplemented_marker", {}
    )
    trend = payload["trend"]
    lines = [
        "# RepoGC scan report",
        "",
        f"**Execution reliability: {metadata['reliability']}**",
        "",
    ]
    reasons = metadata.get("reliability_reasons", [])
    if reasons:
        lines.extend(["Reliability notes:", ""])
        lines.extend(f"- {_cell(reason)}" for reason in reasons)
        lines.append("")
    lines.extend(
        [
            "## Metadata",
            "",
            f"- RepoGC version: `{metadata['repogc_version']}`",
            f"- Report schema: `{metadata['report_schema_version']}`",
            f"- Generated at: `{metadata['generated_at']}`",
            f"- Commit: `{metadata['repository'].get('commit') or 'unavailable'}`",
            f"- Branch: `{metadata['repository'].get('branch') or 'unavailable'}`",
            f"- Working tree dirty: `{metadata['repository'].get('dirty')}`",
            f"- Scanner hash: `{metadata['scanner_hash']}`",
            f"- Config hash: `{metadata['config_hash']}`",
            f"- AI annotation: `{metadata['ai_annotation_status']}`",
            f"- Scan integrity: `{metadata['scan_integrity']}`",
            f"- Coverage: `{metadata['coverage']['status']}`",
            f"- Scanned files: `{metadata['scanned_files']}`",
            "",
            "## Coverage",
            "",
            metadata["coverage"]["meaning"],
            "",
            "| Surface | Status |",
            "|---|---|",
        ]
    )
    lines.extend(
        f"| {_cell(surface['name'])} | {_cell(surface['status'])} |"
        for surface in metadata["coverage"]["surfaces"]
    )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Broken references: {summary['broken_reference']}",
            f"- Orphan candidates: {summary['orphan_candidate']}",
            f"- Unimplemented markers: {summary['unimplemented_marker']}",
            f"- Duplicate candidates: {summary['duplicate_candidate']}",
            f"- Unreachable candidates: {summary['unreachable_candidate']}",
            "",
            "Missing-target evidence tiers:",
            "",
            f"- Strong typed edges: {evidence_summary['strong_missing_target_edges']}",
            f"- Contextual typed edges: {evidence_summary['contextual_missing_target_edges']}",
            f"- Contract-sensitive edges: {evidence_summary['contract_sensitive_missing_target_edges']}",
            f"- Contract-sensitive review candidates: {sum(evidence_summary['contract_sensitive_findings_by_category'].values())}",
            f"- Artifact liveness profiles: {evidence_summary['liveness_profiles']}",
            f"- Profiles with observed static inbound evidence: {evidence_summary['profiles_with_static_inbound']}",
            f"- Profiles reachable from configured roots: {evidence_summary['profiles_reachable_from_roots']}",
            f"- Human liveness declarations: {evidence_summary['liveness_declarations']}",
            f"- Declarations matched to review subjects: {evidence_summary['matched_liveness_declarations']}",
            f"- Declarations not present in this report's review subjects: {evidence_summary['unmatched_liveness_declarations']}",
            "",
            "Marker evidence tiers:",
            "",
            f"- Review: {marker_strengths.get('review', 0)}",
            f"- Contextual: {marker_strengths.get('contextual', 0)}",
            "",
            "| Marker context | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {_cell(kind)} | {count} |" for kind, count in sorted(marker_kinds.items())
    )
    lines.extend(
        [
            "",
            "## Trend",
            "",
            f"- Baseline present: `{trend.get('baseline_present', False)}`",
            f"- New: {trend.get('new', 0)}",
            f"- Persistent: {trend.get('persistent', 0)}",
            f"- Resolved: {trend.get('resolved', 0)}",
            f"- Basis changed: `{trend.get('basis_changed', False)}`",
        ]
    )
    basis_reasons = trend.get("basis_change_reasons", [])
    if basis_reasons:
        lines.append(f"- Basis change reasons: {_cell(', '.join(basis_reasons))}")
    lines.extend(
        [
            "",
            "> Execution reliability does not mean semantic completeness. Findings are mechanical evidence and review candidates, not deletion verdicts.",
            "",
            "## Liveness evidence boundary",
            "",
            "Each review subject has a multi-dimensional evidence profile in the JSON report.",
            "`NOT_OBSERVED` means the configured static scan did not see evidence; it does not prove absence.",
            "Without explicit human declarations, dynamic consumers, external systems, and runtime access remain `UNKNOWN`; business meaning remains `NOT_INFERRED`.",
            "Human declarations are shown as `DECLARED`; they do not suppress Findings or alter reachability.",
            "Use `repogc explain FINDING_ID` to inspect the profile for one finding.",
            "",
            "## Evidence graph",
            "",
            f"- Existing artifacts: {sum(1 for artifact in payload['artifacts'] if artifact['exists'])}",
            f"- Unresolved target nodes: {sum(1 for artifact in payload['artifacts'] if not artifact['exists'])}",
            f"- Declared roots: {sum(1 for artifact in payload['artifacts'] if artifact['root'])}",
            f"- Reachable artifacts: {sum(1 for artifact in payload['artifacts'] if artifact['reachable'])}",
            f"- Typed edges: {len(payload['edges'])}",
            "",
            "## Findings",
            "",
        ]
    )
    if not payload["findings"]:
        lines.append("No findings in the configured scan surface.")
    else:
        lines.extend(
            [
                "| ID | Category | Evidence kind | Strength | Source | Target | Evidence | Contract sensitive | Line |",
                "|---|---|---|---|---|---|---|---:|---:|",
            ]
        )
        for finding in payload["findings"]:
            lines.append(
                "| {id} | {category} | {kind} | {strength} | {source} | {target} | {evidence} | {contract} | {line} |".format(
                    id=_cell(finding["id"]),
                    category=_cell(finding["category"]),
                    kind=_cell(finding["evidence_kind"]),
                    strength=_cell(finding["evidence_strength"]),
                    source=_cell(finding["source"]),
                    target=_cell(finding["target"]),
                    evidence=_cell(finding["evidence"]),
                    contract=_cell(finding["contract_sensitive"]),
                    line=_cell(finding["line"]),
                )
            )
    lines.extend(
        [
            "",
            "## Known limits",
            "",
            "This static scan may not observe dynamic, external, human-only, or runtime consumers.",
            "Review all liveness dimensions before changing any reported artifact.",
            "",
        ]
    )
    return "\n".join(lines)


def safe_output_path(root: Path, relative: str) -> Path:
    requested = Path(relative)
    if requested.is_absolute():
        raise ValueError("Report and baseline paths must be relative to the repository root")
    root_resolved = root.resolve()
    resolved = (root_resolved / requested).resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError("Output path escapes the repository root")
    return resolved


def write_reports(root: Path, payload: dict[str, Any], markdown_path: str, json_path: str) -> None:
    markdown_output = safe_output_path(root, markdown_path)
    json_output = safe_output_path(root, json_path)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
