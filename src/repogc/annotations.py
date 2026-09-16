from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

from repogc import REPORT_SCHEMA_VERSION


ANNOTATION_SCHEMA_VERSION = "0.1"
MAX_ANNOTATION_INPUT_BYTES = 1_000_000

_ANNOTATION_FIELDS = {
    "finding_id",
    "observed_background",
    "evidence_sources",
    "uncertainties",
    "human_checks",
}
_INPUT_FIELDS = {"provider", "model", "data_handling", "annotations"}
_FORBIDDEN_VERDICT_TERMS = (
    "delete",
    "remove",
    "keep",
    "retain",
    "retention decision",
    "obsolete",
    "dead code",
    "valuable",
    "worthless",
    "no value",
    "should delete",
    "safe to delete",
    "safe to remove",
    "obsolete and removable",
    "dead file",
    "no longer useful",
    "unused and removable",
    "应该删除",
    "应删除",
    "安全删除",
    "可安全删除",
    "可以放心移除",
    "可以删除",
    "可删除",
    "已无用途",
    "不再有用",
    "没用",
    "无用",
    "删除",
    "移除",
    "保留",
    "留存",
    "废弃",
    "过时",
    "死代码",
    "有价值",
    "无价值",
)


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{name} must be an array of non-empty strings")
    normalized = sorted(set(item.strip() for item in value))
    if not normalized and not allow_empty:
        raise ValueError(f"{name} must contain at least one item")
    return normalized


def _check_verdict_language(values: list[str], name: str) -> None:
    text = unicodedata.normalize("NFKC", "\n".join(values)).casefold()
    found = [term for term in _FORBIDDEN_VERDICT_TERMS if term.casefold() in text]
    if found:
        raise ValueError(
            f"{name} contains forbidden deletion-verdict language: {', '.join(found)}"
        )


def validate_annotation_input(
    report: dict[str, Any], annotation_input: dict[str, Any]
) -> dict[str, Any]:
    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Mechanical report metadata must be an object")
    reliability = metadata.get("reliability")
    if reliability == "UNRELIABLE":
        raise ValueError("An UNRELIABLE mechanical report cannot be annotated")
    if reliability not in {"RELIABLE", "PARTIAL"}:
        raise ValueError("Mechanical report reliability is missing or invalid")
    report_schema = _nonempty_string(
        metadata.get("report_schema_version"),
        "Mechanical report Schema",
    )
    if report_schema != REPORT_SCHEMA_VERSION:
        raise ValueError(
            f"Mechanical report Schema {report_schema} is not supported; "
            f"expected {REPORT_SCHEMA_VERSION}"
        )
    scanner_hash = _nonempty_string(
        metadata.get("scanner_hash"),
        "Mechanical report scanner hash",
    )
    config_hash = _nonempty_string(
        metadata.get("config_hash"),
        "Mechanical report config hash",
    )

    findings = report.get("findings")
    artifacts = report.get("artifacts")
    if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
        raise ValueError("Mechanical report findings must be an array of objects")
    if not isinstance(artifacts, list) or not all(isinstance(item, dict) for item in artifacts):
        raise ValueError("Mechanical report artifacts must be an array of objects")
    finding_ids = [str(item.get("id")) for item in findings if item.get("id")]
    if len(finding_ids) != len(findings):
        raise ValueError("Mechanical report contains a Finding without an ID")
    if len(finding_ids) != len(set(finding_ids)):
        raise ValueError("Mechanical report contains duplicate Finding IDs")
    findings_by_id = dict(zip(finding_ids, findings, strict=False))
    artifact_paths = {
        str(item.get("path"))
        for item in artifacts
        if item.get("path") and item.get("exists") and item.get("scanned")
    }

    if not isinstance(annotation_input, dict):
        raise ValueError("Annotation input must be a JSON object")
    extra_input_fields = sorted(set(annotation_input) - _INPUT_FIELDS)
    if extra_input_fields:
        raise ValueError(
            "Annotation input contains unsupported fields: "
            + ", ".join(extra_input_fields)
        )
    provider = _nonempty_string(annotation_input.get("provider"), "provider")
    model = _nonempty_string(annotation_input.get("model"), "model")
    data_handling = _nonempty_string(
        annotation_input.get("data_handling"), "data_handling"
    )
    annotations = annotation_input.get("annotations")
    if not isinstance(annotations, list):
        raise ValueError("annotations must be an array")

    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, annotation in enumerate(annotations):
        name = f"annotations[{index}]"
        if not isinstance(annotation, dict):
            raise ValueError(f"{name} must be an object")
        extra_fields = sorted(set(annotation) - _ANNOTATION_FIELDS)
        if extra_fields:
            raise ValueError(f"{name} contains unsupported fields: {', '.join(extra_fields)}")
        finding_id = _nonempty_string(annotation.get("finding_id"), f"{name}.finding_id")
        if finding_id not in findings_by_id:
            raise ValueError(f"{name} refers to an unknown Finding ID: {finding_id}")
        if finding_id in seen_ids:
            raise ValueError(f"Duplicate annotation for Finding ID: {finding_id}")
        seen_ids.add(finding_id)
        background = _nonempty_string(
            annotation.get("observed_background"),
            f"{name}.observed_background",
        )
        evidence_sources = _string_list(
            annotation.get("evidence_sources"),
            f"{name}.evidence_sources",
        )
        unknown_sources = sorted(set(evidence_sources) - artifact_paths)
        if unknown_sources:
            raise ValueError(
                f"{name}.evidence_sources contains paths outside the mechanical report: "
                + ", ".join(unknown_sources)
            )
        uncertainties = _string_list(
            annotation.get("uncertainties"),
            f"{name}.uncertainties",
        )
        human_checks = _string_list(
            annotation.get("human_checks"),
            f"{name}.human_checks",
        )
        _check_verdict_language(
            [background, *uncertainties, *human_checks],
            name,
        )
        validated.append(
            {
                "finding_id": finding_id,
                "observed_background": background,
                "evidence_sources": evidence_sources,
                "uncertainties": uncertainties,
                "human_checks": human_checks,
                "ai_generated": True,
                "human_verified": False,
            }
        )

    validated.sort(key=lambda item: item["finding_id"])
    repository = metadata.get("repository")
    if not isinstance(repository, dict):
        repository = {}
    report_sha256 = hashlib.sha256(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "annotation_schema_version": ANNOTATION_SCHEMA_VERSION,
        "mechanical_report": {
            "report_schema_version": report_schema,
            "canonical_report_sha256": report_sha256,
            "repository_commit": repository.get("commit"),
            "scanner_hash": scanner_hash,
            "config_hash": config_hash,
            "reliability": reliability,
        },
        "producer": {
            "provider": provider,
            "model": model,
            "data_handling": data_handling,
        },
        "annotations": validated,
        "mechanical_report_modified": False,
        "disclaimer": (
            "AI-generated background is unverified and supplies no deletion, retention, or value verdict."
        ),
    }


def validate_annotation_sidecar(
    report: dict[str, Any], sidecar: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(sidecar, dict):
        raise ValueError("Annotation sidecar must be a JSON object")
    producer = sidecar.get("producer")
    annotations = sidecar.get("annotations")
    if not isinstance(producer, dict) or not isinstance(annotations, list):
        raise ValueError("Annotation sidecar producer and annotations are required")

    input_annotations: list[dict[str, Any]] = []
    expected_fields = {
        "finding_id",
        "observed_background",
        "evidence_sources",
        "uncertainties",
        "human_checks",
        "ai_generated",
        "human_verified",
    }
    for index, annotation in enumerate(annotations):
        if not isinstance(annotation, dict):
            raise ValueError(f"annotations[{index}] must be an object")
        extra_fields = sorted(set(annotation) - expected_fields)
        if extra_fields:
            raise ValueError(
                f"annotations[{index}] contains unsupported fields: "
                + ", ".join(extra_fields)
            )
        if annotation.get("ai_generated") is not True:
            raise ValueError(f"annotations[{index}].ai_generated must be true")
        if annotation.get("human_verified") is not False:
            raise ValueError(f"annotations[{index}].human_verified must be false")
        input_annotations.append(
            {
                key: annotation.get(key)
                for key in _ANNOTATION_FIELDS
            }
        )

    rebuilt = validate_annotation_input(
        report,
        {
            "provider": producer.get("provider"),
            "model": producer.get("model"),
            "data_handling": producer.get("data_handling"),
            "annotations": input_annotations,
        },
    )
    if sidecar != rebuilt:
        raise ValueError("Annotation sidecar does not match the mechanical report")
    return rebuilt
