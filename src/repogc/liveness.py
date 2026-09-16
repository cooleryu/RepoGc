from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from repogc.models import Artifact, Edge, Finding


OBSERVED = "OBSERVED"
NOT_OBSERVED = "NOT_OBSERVED"
DECLARED = "DECLARED"
UNKNOWN = "UNKNOWN"
NOT_INFERRED = "NOT_INFERRED"
NOT_APPLICABLE = "NOT_APPLICABLE"


def finding_subject_paths(finding: Finding | Mapping[str, Any]) -> tuple[str, ...]:
    if isinstance(finding, Finding):
        source = finding.source
        target = finding.target
    else:
        source = str(finding.get("source") or "")
        raw_target = finding.get("target")
        target = str(raw_target) if raw_target else None
    return tuple(dict.fromkeys(path for path in (source, target) if path))


def _dimension(status: str, evidence: str) -> dict[str, str]:
    return {"status": status, "evidence": evidence}


def build_liveness_profiles(
    artifacts: Iterable[Artifact],
    edges: Iterable[Edge],
    subject_paths: Iterable[str],
    git_last_touch_by_path: Mapping[str, dict[str, str] | None] | None = None,
    declarations: Iterable[Mapping[str, str]] = (),
) -> list[dict[str, Any]]:
    """Build bounded evidence profiles without inferring artifact value.

    NOT_OBSERVED only means that the configured static scan did not see evidence.
    UNKNOWN is reserved for surfaces this scanner did not inspect.
    """

    artifacts_by_path = {artifact.path: artifact for artifact in artifacts}
    incoming_by_target: dict[str, list[Edge]] = {}
    for edge in edges:
        if edge.source == edge.target:
            continue
        incoming_by_target.setdefault(edge.target, []).append(edge)
    git_context = git_last_touch_by_path or {}
    declarations_by_path: dict[str, list[dict[str, str]]] = {}
    for declaration in declarations:
        normalized = {
            "path": str(declaration["path"]),
            "kind": str(declaration["kind"]),
            "source": str(declaration["source"]),
            "reason": str(declaration["reason"]),
        }
        declarations_by_path.setdefault(normalized["path"], []).append(normalized)
    for declared in declarations_by_path.values():
        declared.sort(key=lambda item: (item["kind"], item["source"], item["reason"]))

    profiles: list[dict[str, Any]] = []
    for path in sorted(set(subject_paths)):
        artifact = artifacts_by_path.get(path)
        if artifact is None:
            continue
        incoming = sorted(
            incoming_by_target.get(path, []),
            key=lambda item: (item.source, item.kind, item.id),
        )
        strong = [edge for edge in incoming if edge.strength == "strong"]
        contextual = [edge for edge in incoming if edge.strength == "contextual"]
        contract_edges = [edge for edge in incoming if edge.contract_sensitive]
        workflow_kinds = {
            "ci_reference",
            "config_reference",
            "state_reference",
            "test_reference",
        }
        workflow_edges = [edge for edge in incoming if edge.kind in workflow_kinds]
        last_touch = git_context.get(path)
        declared_evidence = declarations_by_path.get(path, [])

        def declaration_dimension(kind: str, unknown_evidence: str) -> dict[str, str]:
            matching = [item for item in declared_evidence if item["kind"] == kind]
            if not matching:
                return _dimension(UNKNOWN, unknown_evidence)
            evidence = "; ".join(
                f"{item['source']}: {item['reason']}" for item in matching
            )
            return _dimension(DECLARED, evidence)

        if not artifact.exists:
            reachability = _dimension(
                NOT_APPLICABLE,
                "The referenced artifact does not exist in the inspected repository snapshot.",
            )
        elif artifact.reachable:
            reachability = _dimension(
                OBSERVED,
                " -> ".join(artifact.evidence_path),
            )
        else:
            reachability = _dimension(
                NOT_OBSERVED,
                "No traversable path from a configured root was observed.",
            )

        dimensions: dict[str, dict[str, str]] = {
            "human_declared_root": _dimension(
                OBSERVED if artifact.root else NOT_OBSERVED,
                "Matched a configured root declaration."
                if artifact.root
                else "Did not match the configured root declarations.",
            ),
            "human_declared_retention": _dimension(
                DECLARED
                if any(item["kind"] == "retention" for item in declared_evidence)
                else NOT_OBSERVED,
                "; ".join(
                    f"{item['source']}: {item['reason']}"
                    for item in declared_evidence
                    if item["kind"] == "retention"
                )
                or "No explicit retention declaration matched this artifact.",
            ),
            "root_reachability": reachability,
            "static_inbound_references": _dimension(
                OBSERVED if incoming else NOT_OBSERVED,
                f"{len(incoming)} inbound edge(s): {', '.join(sorted({edge.kind for edge in incoming}))}"
                if incoming
                else "No inbound reference was observed in the configured static scan surface.",
            ),
            "contract_or_instruction_consumer": _dimension(
                OBSERVED if contract_edges else NOT_OBSERVED,
                f"{len(contract_edges)} contract-sensitive inbound edge(s)."
                if contract_edges
                else "No contract-sensitive inbound edge was observed.",
            ),
            "build_test_ci_or_config_consumer": _dimension(
                OBSERVED if workflow_edges else NOT_OBSERVED,
                f"{len(workflow_edges)} workflow/config/test inbound edge(s)."
                if workflow_edges
                else "No build, test, CI, state, or config consumer was observed.",
            ),
            "git_last_touch": _dimension(
                OBSERVED if last_touch else UNKNOWN,
                f"{last_touch['date']} at {last_touch['commit']}"
                if last_touch
                else "Git last-touch evidence was unavailable for this review subject.",
            ),
            "dynamic_consumers": declaration_dimension(
                "dynamic_consumer",
                "Dynamic lookup and computed paths were not observed by this static scan.",
            ),
            "external_system_consumers": declaration_dimension(
                "external_system_consumer",
                "External systems were not queried.",
            ),
            "runtime_access": declaration_dimension(
                "runtime_access",
                "Runtime access events were not collected.",
            ),
            "business_meaning": _dimension(
                NOT_INFERRED,
                "RepoGC does not infer business purpose or artifact value.",
            ),
        }
        profiles.append(
            {
                "path": path,
                "role": artifact.role,
                "exists": artifact.exists,
                "scanned": artifact.scanned,
                "incoming_edge_counts": {
                    "strong": len(strong),
                    "contextual": len(contextual),
                    "contract_sensitive": len(contract_edges),
                },
                "incoming_edge_kinds": sorted({edge.kind for edge in incoming}),
                "incoming_sources": sorted({edge.source for edge in incoming}),
                "declared_evidence": declared_evidence,
                "dimensions": dimensions,
                "verdict_boundary": (
                    "This profile is evidence availability, not a deletion, retention, or value verdict."
                ),
            }
        )
    return profiles
