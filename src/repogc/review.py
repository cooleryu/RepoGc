from __future__ import annotations

import hashlib
from typing import Any


REVIEW_SCHEMA_VERSION = "0.1"
DEFAULT_REVIEW_LIMIT = 5
MAX_REVIEW_LIMIT = 5


def _concern_kind(category: str) -> str:
    if category in {"orphan_candidate", "unreachable_candidate"}:
        return "unclear_navigation"
    return category


def _is_default_review_evidence(
    finding: dict[str, Any], profile: dict[str, Any] | None
) -> bool:
    category = finding.get("category")
    if category == "unimplemented_marker":
        return (
            finding.get("evidence_strength") == "review"
            or finding.get("evidence_kind") == "operational_state_marker"
        )
    if (
        category == "broken_reference"
        and finding.get("evidence_strength") != "strong"
    ):
        if profile is None:
            return False
        return bool(profile.get("root")) or profile.get("role") in {
            "skill",
            "agent_instruction",
            "harness_state",
        }
    return True


def _unique(values: list[str], limit: int | None = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(value.split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if limit is not None and len(result) >= limit:
            break
    return result


def _finding_score(finding: dict[str, Any]) -> int:
    category = finding.get("category")
    strength = finding.get("evidence_strength")
    kind = finding.get("evidence_kind")
    if category == "broken_reference":
        if strength == "strong":
            return 100
        return {
            "path_mention": 25,
            "test_reference": 40,
            "example_reference": 50,
        }.get(str(kind), 35)
    if category == "unimplemented_marker":
        if kind == "operational_state_marker":
            return 95 if strength == "review" else 90
        return 95 if strength == "review" else 30
    if category == "orphan_candidate":
        return 85
    if category == "unreachable_candidate":
        return 85 if finding.get("contract_sensitive") else 80
    if category == "duplicate_candidate":
        return 60
    return 10


def _headline(findings: list[dict[str, Any]]) -> str:
    categories = {str(item.get("category")) for item in findings}
    markers = [item for item in findings if item.get("category") == "unimplemented_marker"]
    if markers:
        status_count = sum(item.get("evidence_kind") == "operational_state_marker" for item in markers)
        if status_count == len(markers):
            return "A status note may be out of date"
        if status_count:
            return "Work and status notes need checking"
        return "An unfinished-work marker needs checking"
    if {"orphan_candidate", "unreachable_candidate"} <= categories:
        return "A document has no clear project entry"
    if "orphan_candidate" in categories:
        return "A document has no clear project entry"
    if "unreachable_candidate" in categories:
        return "A document has no clear project entry"
    if "broken_reference" in categories:
        kinds = {str(item.get("evidence_kind")) for item in findings}
        if "example_reference" in kinds:
            return "An example path needs clarification"
        if "test_reference" in kinds:
            return "A test path needs clarification"
        if "path_mention" in kinds:
            return "Some document paths need clarification"
        return "A referenced path was not found"
    if "duplicate_candidate" in categories:
        return "Two files contain very similar text"
    return "This file needs a closer look"


def _what_was_found(findings: list[dict[str, Any]]) -> list[str]:
    counts: dict[str, int] = {}
    for finding in findings:
        category = str(finding.get("category"))
        counts[category] = counts.get(category, 0) + 1
    messages: list[str] = []
    if counts.get("broken_reference"):
        kinds = {str(item.get("evidence_kind")) for item in findings}
        if "example_reference" in kinds:
            messages.append("An example mentions a path that was not found on disk.")
        elif "test_reference" in kinds:
            messages.append("A test mentions a path that was not found on disk.")
        elif any(item.get("evidence_strength") == "strong" for item in findings):
            messages.append(
                "A referenced path was not found in the configured scan."
            )
        else:
            messages.append("Some paths mentioned in this document were not found on disk.")
    if counts.get("orphan_candidate"):
        messages.append("No incoming reference was observed in the configured scan.")
    if counts.get("unreachable_candidate"):
        messages.append("No supported path from a configured project entry was observed.")
    if counts.get("unimplemented_marker"):
        status_count = sum(item.get("category") == "unimplemented_marker" and
                           item.get("evidence_kind") == "operational_state_marker" for item in findings)
        task_count = counts["unimplemented_marker"] - status_count
        if status_count:
            messages.append(f"{status_count} point-in-time status statement"
                            f"{'s' if status_count != 1 else ''} may no longer match the project.")
        if task_count:
            messages.append(f"{task_count} unfinished-work marker{'s' if task_count != 1 else ''} "
                            "need checking against implementation and project intent.")
    if counts.get("duplicate_candidate"):
        messages.append("A highly similar document was observed elsewhere in the repository.")
    return messages


def _mechanical_context(
    findings: list[dict[str, Any]], profile: dict[str, Any] | None
) -> list[str]:
    kinds = {str(item.get("evidence_kind")) for item in findings}
    role = None if profile is None else profile.get("role")
    context: list[str] = []
    if "example_reference" in kinds:
        context.append(
            "At least one path appears in an example, where indentation or generated files may change its meaning."
        )
    if "test_reference" in kinds:
        context.append(
            "At least one path appears in a test, which may create temporary fixtures at runtime."
        )
    if "path_mention" in kinds:
        context.append("Plain-text path mentions are weaker than code or configuration dependencies.")
    if "operational_state_marker" in kinds:
        context.append(
            "The wording looks like a point-in-time status statement, so its date and later work matter."
        )
    if kinds & {
        "test_marker",
        "string_literal_marker",
        "example_marker",
        "marker_term_reference",
    }:
        context.append("Some marker text occurs in a test, string, or explanatory example.")
    if role == "harness_state":
        context.append(
            "Harness state and audit documents may have human or workflow consumers that static links do not expose."
        )
    if role in {"skill", "agent_instruction"}:
        context.append("Agent hosts may load instruction files by repository convention.")
    if "duplicate_candidate" in {str(item.get("category")) for item in findings}:
        context.append("Text similarity can come from a shared template or different audiences.")
    if profile is not None:
        dimensions = profile.get("dimensions", {})
        inbound = dimensions.get("static_inbound_references", {})
        if inbound.get("status") == "OBSERVED":
            context.append("The scan did observe incoming references, although they may be contextual.")
    return _unique(context, limit=3)


def _unknowns(profile: dict[str, Any] | None) -> list[str]:
    if profile is None:
        return ["Project intent and runtime use were not established by the static scan."]
    dimensions = profile.get("dimensions", {})
    labels = (
        ("dynamic_consumers", "Whether computed or dynamic lookups use this file."),
        ("external_system_consumers", "Whether systems outside the repository use this file."),
        ("runtime_access", "Whether running software reads this file."),
        ("business_meaning", "What purpose this file currently serves for the project."),
    )
    values = [
        label
        for name, label in labels
        if dimensions.get(name, {}).get("status") in {"UNKNOWN", "NOT_INFERRED"}
    ]
    return _unique(values, limit=3)


def _human_checks(findings: list[dict[str, Any]]) -> list[str]:
    categories = {str(item.get("category")) for item in findings}
    checks: list[str] = []
    if "broken_reference" in categories:
        checks.append("Confirm the intended base directory or whether the path is created at runtime.")
    if "unimplemented_marker" in categories:
        checks.append("Compare the statement with newer implementation notes and tests.")
    if "orphan_candidate" in categories:
        checks.append("Confirm whether people, agents, or external workflows still use this file.")
    if "unreachable_candidate" in categories:
        checks.append("Confirm which project entry is expected to lead to this file.")
    if "duplicate_candidate" in categories:
        checks.append("Confirm whether the similar files serve different audiences or contracts.")
    return checks[:3]


def _select_groups(
    groups: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    ranked = sorted(
        groups,
        key=lambda item: (-item["score"], item["category"], item["subject"]),
    )
    selected: list[dict[str, Any]] = []
    selected_concerns: set[str] = set()
    selected_subjects: set[str] = set()

    # First show one representative concern of each kind on a different file.
    for group in ranked:
        if len(selected) >= limit:
            break
        if (
            group["concern_kind"] not in selected_concerns
            and group["subject"] not in selected_subjects
        ):
            selected.append(group)
            selected_concerns.add(group["concern_kind"])
            selected_subjects.add(group["subject"])

    # A repository may expose two concern kinds on the same only subject.
    for group in ranked:
        if len(selected) >= limit:
            break
        if group["concern_kind"] not in selected_concerns:
            selected.append(group)
            selected_concerns.add(group["concern_kind"])

    return sorted(
        selected,
        key=lambda item: (-item["score"], item["category"], item["subject"]),
    )


def build_review_payload(
    report: dict[str, Any],
    *,
    annotations: dict[str, Any] | None = None,
    limit: int = DEFAULT_REVIEW_LIMIT,
) -> dict[str, Any]:
    if not 1 <= limit <= MAX_REVIEW_LIMIT:
        raise ValueError(f"review limit must be between 1 and {MAX_REVIEW_LIMIT}")
    metadata = report.get("metadata")
    findings = report.get("findings")
    if not isinstance(metadata, dict) or not isinstance(findings, list):
        raise ValueError("Mechanical report metadata and findings are required")
    reliability = metadata.get("reliability")
    if reliability == "UNRELIABLE":
        raise ValueError("Mechanical scan is UNRELIABLE; run repogc doctor before review")
    if reliability not in {"RELIABLE", "PARTIAL"}:
        raise ValueError("Mechanical report reliability is missing or invalid")
    if not all(isinstance(item, dict) for item in findings):
        raise ValueError("Mechanical report findings must be objects")

    profile_by_path = {
        str(profile.get("path")): profile
        for profile in report.get("artifact_liveness", [])
        if isinstance(profile, dict) and profile.get("path")
    }
    annotation_by_id = {
        str(item.get("finding_id")): item
        for item in ([] if annotations is None else annotations.get("annotations", []))
        if isinstance(item, dict) and item.get("finding_id")
    }
    findings_by_source: dict[str, list[dict[str, Any]]] = {}
    review_signal_count = 0
    for finding in findings:
        source = finding.get("source")
        profile = profile_by_path.get(str(source))
        if (
            source
            and (profile is None or profile.get("role") != "generated")
            and _is_default_review_evidence(finding, profile)
        ):
            findings_by_source.setdefault(str(source), []).append(finding)
            review_signal_count += 1

    groups: list[dict[str, Any]] = []
    for subject, subject_findings in findings_by_source.items():
        by_category: dict[str, list[dict[str, Any]]] = {}
        for finding in subject_findings:
            by_category.setdefault(str(finding.get("category")), []).append(finding)
        for category, category_findings in by_category.items():
            ordered = sorted(category_findings, key=lambda item: str(item.get("id")))
            groups.append(
                {
                    "subject": subject,
                    "findings": ordered,
                    "category": category,
                    "concern_kind": _concern_kind(category),
                    "score": max(_finding_score(item) for item in ordered),
                }
            )

    cards: list[dict[str, Any]] = []
    for group in _select_groups(groups, limit):
        subject = group["subject"]
        subject_findings = group["findings"]
        profile = profile_by_path.get(subject)
        matching_annotations = [
            annotation_by_id[str(item.get("id"))]
            for item in subject_findings
            if str(item.get("id")) in annotation_by_id
        ]
        context = [
            str(item.get("observed_background")) for item in matching_annotations
        ]
        context.extend(_mechanical_context(subject_findings, profile))
        unknowns = _unknowns(profile)
        for item in matching_annotations:
            unknowns.extend(str(value) for value in item.get("uncertainties", []))
        checks: list[str] = []
        for item in matching_annotations:
            checks.extend(str(value) for value in item.get("human_checks", []))
        checks.extend(_human_checks(subject_findings))
        finding_ids = sorted(str(item.get("id")) for item in subject_findings)
        card_id = hashlib.sha1(
            (subject + "\0" + "\0".join(finding_ids)).encode("utf-8")
        ).hexdigest()[:12]
        cards.append(
            {
                "id": card_id,
                "subject": subject,
                "headline": _headline(subject_findings),
                "what_was_found": _what_was_found(subject_findings),
                "context": _unique(context, limit=4),
                "unknowns": _unique(unknowns, limit=4),
                "human_checks": _unique(checks, limit=4),
                "ai_context_used": bool(matching_annotations),
                "finding_count": len(subject_findings),
                "finding_ids": finding_ids,
                "concern_kind": group["concern_kind"],
                "categories": [group["category"]],
            }
        )

    repository = metadata.get("repository")
    if not isinstance(repository, dict):
        repository = {}
    return {
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "repository": {
            "commit": repository.get("commit"),
            "branch": repository.get("branch"),
        },
        "reliability": reliability,
        "reliability_notes": metadata.get("reliability_reasons", []),
        "raw_signal_count": len(findings),
        "review_signal_count": review_signal_count,
        "suppressed_default_signal_count": len(findings) - review_signal_count,
        "review_subject_count": len(groups),
        "shown_count": len(cards),
        "ai_context_used": any(card["ai_context_used"] for card in cards),
        "cards": cards,
        "safety": {
            "files_changed": False,
            "action_verdict": False,
            "message": "Review cards organize evidence for a person; they do not decide what action to take.",
        },
    }


def render_review(payload: dict[str, Any]) -> str:
    cards = payload["cards"]
    lines = [
        (
            f"RepoGC review — {len(cards)} item{'s' if len(cards) != 1 else ''} "
            f"from {payload['raw_signal_count']} scan signals"
        ),
        "Read-only: no files changed, no keep/delete decision made.",
    ]
    if payload["ai_context_used"]:
        lines.append("Codex added repository context for selected evidence.")
    if payload["reliability"] == "PARTIAL":
        lines.append("Note: the scan had incomplete coverage; treat every card cautiously.")
    if not cards:
        lines.extend(["", "No distinct concern reached the default review surface."])
        return "\n".join(lines)
    for index, card in enumerate(cards, start=1):
        lines.extend(
            ["", f"{index}. {card['headline']} — {card['subject']}"]
        )
        for label, key in (
            ("Why", "what_was_found"),
            ("Context", "context"),
            ("Check", "human_checks"),
        ):
            values = card[key]
            if values:
                lines.append(f"   {label}: {values[0]}")
    lines.extend(
        [
            "",
            "Limits: runtime use, external systems, and project intent remain unknown.",
        ]
    )
    return "\n".join(lines)
