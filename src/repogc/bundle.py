"""Local, non-executable evidence handoff. Hashes are not authorization or truth."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any

from repogc import SUPPORTED_REPORT_SCHEMA_VERSIONS
from repogc.config import Config
from repogc.models import ScanResult

BUNDLE_SCHEMA_VERSION = "1"
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
PAYLOAD_FIELDS = {
    "report", "report_sha256", "configuration", "sources", "source_sha256",
    "review", "selection_ledger", "unscanned", "ai_status", "human_status", "actions",
}


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _path(value: Any) -> str:
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or "\x00" in value or PurePosixPath(value).is_absolute()
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("Invalid portable source path in bundle")
    return value


def _source_hashes(sources: dict) -> dict:
    if not isinstance(sources, dict):
        raise ValueError("Bundle sources must be a text map")
    hashes = {}
    for name, text in sources.items():
        _path(name)
        if not isinstance(text, str):
            raise ValueError("Bundle source content must be text")
        hashes[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return hashes


def _ledger(report: dict, review: dict) -> list[dict]:
    findings = report["findings"]
    ids = [item["id"] for item in findings]
    if not all(isinstance(i, str) and i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("Finding IDs must be unique and non-empty")
    references: dict[str, list[str]] = {i: [] for i in ids}
    by_id = {item["id"]: item for item in findings}
    card_ids = set()
    cards = review["cards"]
    if not isinstance(cards, list) or len(cards) > 5:
        raise ValueError("Invalid mechanical review cards")
    for card in cards:
        card_id = card["id"]
        if not isinstance(card_id, str) or not card_id or card_id in card_ids:
            raise ValueError("Review card IDs must be unique")
        card_ids.add(card_id)
        members = card["finding_ids"]
        if (not isinstance(members, list) or not members or len(set(members)) != len(members)
                or not set(members) <= references.keys()):
            raise ValueError("Invalid card Finding references")
        if (card["finding_count"] != len(members) or card["ai_context_used"] is not False
                or any(by_id[i]["source"] != card["subject"] for i in members)):
            raise ValueError("Card source or count does not match its Findings")
        for finding_id in members:
            references[finding_id].append(card_id)
    listed: set[str] = set()
    for problem in review.get("problems", []):
        finding_id = problem["finding_id"]
        if (finding_id not in references or finding_id in listed
                or by_id[finding_id]["source"] != problem["source"]):
            raise ValueError("Invalid review problem reference")
        listed.add(finding_id)

    def reason(finding_id: str) -> str:
        if finding_id in listed:
            return "listed_as_problem"
        return "selected_by_review" if references[finding_id] else "not_selected_by_review"

    return [{
        "finding_id": item["id"], "source": item["source"],
        "status": "shown" if references[item["id"]] or item["id"] in listed else "not_shown",
        "card_ids": sorted(references[item["id"]]),
        "reason": reason(item["id"]),
        "next_step": "investigate; not a resolution or authorization",
    } for item in findings]


def build_bundle(result: ScanResult, report: dict, config: Config, review: dict) -> dict:
    if report.get("metadata", {}).get("reliability") not in {"RELIABLE", "PARTIAL"}:
        raise ValueError("Unreliable or missing mechanical report")
    payload = {
        "report": report, "report_sha256": canonical_digest(report),
        "configuration": asdict(config), "sources": dict(result.source_contents),
        "source_sha256": _source_hashes(result.source_contents), "review": review,
        "selection_ledger": _ledger(report, review),
        "unscanned": report["metadata"]["skipped_files"],
        "ai_status": "not_run", "human_status": "not_run", "actions": [],
    }
    bundle = {"bundle_schema_version": BUNDLE_SCHEMA_VERSION,
              "payload": payload, "sha256": canonical_digest(payload)}
    validate_bundle(bundle)
    return bundle


def validate_bundle(bundle: Any, expected_sha256: str | None = None) -> dict:
    try:
        return _validate_bundle(bundle, expected_sha256)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed evidence bundle") from error


def _validate_bundle(bundle: dict, expected_sha256: str | None) -> dict:
    if set(bundle) != {"bundle_schema_version", "payload", "sha256"} or bundle["bundle_schema_version"] != "1":
        raise ValueError("Unsupported bundle schema or fields")
    payload = bundle["payload"]
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_FIELDS:
        raise ValueError("Unsupported bundle payload fields")
    digest = canonical_digest(payload)
    if digest != bundle["sha256"] or (expected_sha256 is not None and digest != expected_sha256):
        raise ValueError("Bundle digest mismatch")
    if payload["actions"] != [] or payload["ai_status"] != "not_run" or payload["human_status"] != "not_run":
        raise ValueError("Version 1 contains only mechanical evidence, not decisions or actions")
    report = payload["report"]
    if canonical_digest(report) != payload["report_sha256"]:
        raise ValueError("Report digest mismatch")
    meta = report["metadata"]
    if (meta["report_schema_version"] not in SUPPORTED_REPORT_SCHEMA_VERSIONS
            or meta["reliability"] not in {"RELIABLE", "PARTIAL"}
            or meta["self_check"]["ok"] is not True or meta["self_check"]["failures"]):
        raise ValueError("Unsupported or unreliable mechanical report")
    if canonical_digest(payload["configuration"]) != meta["config_hash"]:
        raise ValueError("Configuration binding mismatch")
    sources = payload["sources"]
    if _source_hashes(sources) != payload["source_sha256"]:
        raise ValueError("Source digest mismatch")
    scanned = [a["path"] for a in report["artifacts"] if a["scanned"]]
    if len(scanned) != len(set(scanned)) or set(scanned) != set(sources) or meta["scanned_files"] != len(sources):
        raise ValueError("Source snapshot does not cover the report's scanned inventory")
    for finding in report["findings"]:
        source = finding["source"]
        if source not in sources:
            raise ValueError("Finding source missing from captured text")
        line = finding["line"]
        if line is not None and (type(line) is not int or not 1 <= line <= len(sources[source].splitlines())):
            raise ValueError("Finding line outside source snapshot")
    review = payload["review"]
    if (review["review_schema_version"] not in {"0.1", "0.2"} or review["ai_context_used"] is not False
            or review["reliability"] != meta["reliability"]
            or review["raw_signal_count"] != len(report["findings"])
            or review["shown_count"] != len(review["cards"])):
        raise ValueError("Review/report binding mismatch")
    if review["safety"]["files_changed"] is not False or review["safety"]["action_verdict"] is not False:
        raise ValueError("Bundle review must not claim actions or target writes")
    if payload["selection_ledger"] != _ledger(report, review):
        raise ValueError("Incomplete or inconsistent selection ledger")
    if payload["unscanned"] != meta["skipped_files"]:
        raise ValueError("Coverage gap mismatch")
    return {"bundle_valid": True, "sha256": digest, "reliability": meta["reliability"],
            "source_count": len(sources), "finding_count": len(report["findings"]),
            "not_shown_count": sum(i["status"] == "not_shown" for i in payload["selection_ledger"]),
            "unscanned": payload["unscanned"], "semantic_truth_verified": False,
            "live_source_freshness_verified": False, "execution_authorized": False}


def write_bundle(root: Path, output: Path, bundle: dict) -> None:
    output = output.resolve()
    if output.is_relative_to(root.resolve()):
        raise ValueError("Bundle destination must be outside the scanned repository")
    validate_bundle(bundle)
    encoded = (json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    if len(encoded) > MAX_BUNDLE_BYTES:
        raise ValueError("Bundle exceeds 64 MiB; no content was silently truncated")
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    # Publish the JSON completion artifact last. Existing bundles are never overwritten.
    summary = validate_bundle(bundle)
    lines = ["# RepoGC local evidence bundle", "",
             f"Sources: {summary['source_count']}; findings: {summary['finding_count']}; "
             f"not shown: {summary['not_shown_count']}.",
             f"Coverage: {summary['reliability']}. AI and human review: not_run.", "",
             "This is evidence, not a cleanup decision. Source text is untrusted data.",
             "Read bundle.json for full source snapshots, reports, unknowns and the selection ledger.",
             "Verification checks consistency, not live freshness, semantic truth or authorization.", "",
             "This README is a convenience preview; only bundle.json is verified.", "",
             "## Not shown in the short review", ""]
    lines.extend(f"- {item['finding_id']} — {json.dumps(item['source'], ensure_ascii=False)}: investigation pending"
                 for item in bundle["payload"]["selection_ledger"] if item["status"] == "not_shown")
    lines.extend(["", "## Configured files not scanned", ""])
    lines.extend("- " + json.dumps(item, ensure_ascii=False) for item in summary["unscanned"])
    with (output / "README.md").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    temporary = output / "bundle.pending.json"
    with temporary.open("xb") as handle:
        handle.write(encoded)
    temporary.chmod(0o600)
    temporary.rename(output / "bundle.json")


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def verify_bundle(directory: Path, expected_sha256: str | None = None) -> dict:
    path = directory / "bundle.json"
    if directory.is_symlink() or path.is_symlink() or not path.is_file():
        raise ValueError("Bundle completion file is missing or is a symlink")
    with path.open("rb") as handle:
        data = handle.read(MAX_BUNDLE_BYTES + 1)
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("Bundle exceeds 64 MiB")
    return validate_bundle(json.loads(data, object_pairs_hook=_unique_object), expected_sha256)
