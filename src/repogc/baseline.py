from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repogc import BASELINE_SCHEMA_VERSION


def load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Baseline must contain a JSON object")
    return payload


def compare_baseline(
    current_findings: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
    *,
    scanner_hash: str,
    config_hash: str,
    report_schema: str,
) -> dict[str, Any]:
    current_by_id = {str(item["id"]): item for item in current_findings}
    if baseline is None:
        return {
            "baseline_present": False,
            "basis_changed": False,
            "basis_change_reasons": [],
            "new": len(current_by_id),
            "persistent": 0,
            "resolved": 0,
            "new_ids": sorted(current_by_id),
            "persistent_ids": [],
            "resolved_ids": [],
        }

    baseline_findings = baseline.get("findings", [])
    if not isinstance(baseline_findings, list):
        raise ValueError("Baseline findings must be an array")
    baseline_by_id = {str(item["id"]): item for item in baseline_findings}
    reasons: list[str] = []
    if baseline.get("scanner_hash") != scanner_hash:
        reasons.append("scanner_hash changed")
    if baseline.get("config_hash") != config_hash:
        reasons.append("config_hash changed")
    if baseline.get("report_schema_version") != report_schema:
        reasons.append("report_schema_version changed")

    current_ids = set(current_by_id)
    baseline_ids = set(baseline_by_id)
    return {
        "baseline_present": True,
        "basis_changed": bool(reasons),
        "basis_change_reasons": reasons,
        "new": len(current_ids - baseline_ids),
        "persistent": len(current_ids & baseline_ids),
        "resolved": len(baseline_ids - current_ids),
        "new_ids": sorted(current_ids - baseline_ids),
        "persistent_ids": sorted(current_ids & baseline_ids),
        "resolved_ids": sorted(baseline_ids - current_ids),
    }


def baseline_from_report(report: dict[str, Any]) -> dict[str, Any]:
    metadata = report.get("metadata", {})
    if metadata.get("reliability") != "RELIABLE":
        raise ValueError("Only a RELIABLE report may become the formal baseline")
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("Report findings must be an array")
    return {
        "baseline_schema_version": BASELINE_SCHEMA_VERSION,
        "report_schema_version": metadata.get("report_schema_version"),
        "created_at": metadata.get("generated_at"),
        "repository_commit": metadata.get("repository", {}).get("commit"),
        "scanner_hash": metadata.get("scanner_hash"),
        "config_hash": metadata.get("config_hash"),
        "findings": [
            {
                "id": finding.get("id"),
                "category": finding.get("category"),
                "source": finding.get("source"),
                "target": finding.get("target"),
            }
            for finding in findings
        ],
    }


def write_baseline(path: Path, baseline: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
