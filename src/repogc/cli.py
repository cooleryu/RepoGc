from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from repogc import REPORT_SCHEMA_VERSION
from repogc.annotations import (
    ANNOTATION_SCHEMA_VERSION,
    MAX_ANNOTATION_INPUT_BYTES,
    validate_annotation_input,
    validate_annotation_sidecar,
)
from repogc.baseline import (
    baseline_from_report,
    compare_baseline,
    load_baseline,
    write_baseline,
)
from repogc.config import Config, load_config
from repogc.bundle import build_bundle, write_bundle, verify_bundle
from repogc.git_info import repository_info
from repogc.reporting import report_payload, safe_output_path, write_reports
from repogc.review import DEFAULT_REVIEW_LIMIT, build_review_payload, render_review
from repogc.scanner import scan_repository
from repogc.self_check import run_self_check


def _config_path(root: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def _load(root: Path, value: str | None) -> tuple[Config, Path | None]:
    return load_config(root, _config_path(root, value))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _finding_list(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings = report.get("findings", [])
    if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
        raise ValueError("Report findings must be an array of objects")
    return findings


def _finding_trend_status(finding_id: str, trend: dict[str, Any]) -> str:
    if finding_id in trend.get("new_ids", []):
        return "new"
    if finding_id in trend.get("persistent_ids", []):
        return "persistent"
    if finding_id in trend.get("resolved_ids", []):
        return "resolved"
    return "untracked"


def _explanation_payload(report: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
    profile_by_path = {
        str(profile.get("path")): profile
        for profile in report.get("artifact_liveness", [])
        if isinstance(profile, dict) and profile.get("path")
    }
    subjects = finding.get("review_subjects")
    if not isinstance(subjects, list):
        subjects = [finding.get("source"), finding.get("target")]
    subject_profiles = [
        profile_by_path[str(path)]
        for path in subjects
        if path and str(path) in profile_by_path
    ]
    trend = report.get("trend", {})
    if not isinstance(trend, dict):
        trend = {}
    return {
        "finding": finding,
        "trend_status": _finding_trend_status(str(finding.get("id")), trend),
        "artifact_liveness": subject_profiles,
        "verdict_boundary": (
            "This explanation presents mechanical evidence and unknowns; it does not decide whether any artifact should be deleted or retained."
        ),
    }


def _render_explanation(explanation: dict[str, Any]) -> str:
    finding = explanation["finding"]
    lines = [
        f"RepoGC finding {finding.get('id')}",
        f"Category: {finding.get('category')}",
        f"Trend status: {explanation['trend_status']}",
        f"Source: {finding.get('source')}",
        f"Target: {finding.get('target') or 'none'}",
        f"Rule: {finding.get('rule')}",
        f"Evidence kind: {finding.get('evidence_kind', 'unspecified')}",
        f"Evidence strength: {finding.get('evidence_strength', 'unspecified')}",
        f"Contract sensitive: {finding.get('contract_sensitive', False)}",
        f"Mechanical evidence: {finding.get('evidence')}",
        "",
        "Artifact liveness evidence",
    ]
    profiles = explanation["artifact_liveness"]
    if not profiles:
        lines.append("No liveness profile is present in this report. Regenerate it with the current RepoGC version.")
    for profile in profiles:
        lines.extend(
            [
                "",
                f"Subject: {profile['path']} ({profile['role']})",
                f"Exists: {profile['exists']}",
                (
                    "Inbound edges: strong={strong}, contextual={contextual}, contract-sensitive={contract}"
                ).format(
                    strong=profile["incoming_edge_counts"]["strong"],
                    contextual=profile["incoming_edge_counts"]["contextual"],
                    contract=profile["incoming_edge_counts"]["contract_sensitive"],
                ),
            ]
        )
        for name, dimension in profile["dimensions"].items():
            lines.append(f"- {name}: {dimension['status']} — {dimension['evidence']}")
    git_last_touch = finding.get("git_last_touch")
    lines.extend(
        [
            "",
            "Finding review guidance",
            f"Known limitations: {finding.get('known_limitations')}",
            f"Human review: {finding.get('human_review')}",
            (
                "Git last touch: "
                + (
                    f"{git_last_touch.get('date')} at {git_last_touch.get('commit')}"
                    if isinstance(git_last_touch, dict)
                    else "unavailable"
                )
            ),
            "",
            f"Verdict boundary: {explanation['verdict_boundary']}",
        ]
    )
    return "\n".join(lines)


def _diff_payload(
    report: dict[str, Any], baseline: dict[str, Any] | None
) -> dict[str, Any]:
    metadata = report.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("Report metadata must be an object")
    findings = _finding_list(report)
    trend = compare_baseline(
        findings,
        baseline,
        scanner_hash=str(metadata.get("scanner_hash") or ""),
        config_hash=str(metadata.get("config_hash") or ""),
        report_schema=str(metadata.get("report_schema_version") or ""),
    )
    current_by_id = {str(item.get("id")): item for item in findings}
    baseline_findings = [] if baseline is None else baseline.get("findings", [])
    if not isinstance(baseline_findings, list):
        raise ValueError("Baseline findings must be an array")
    baseline_by_id = {
        str(item.get("id")): item
        for item in baseline_findings
        if isinstance(item, dict)
    }

    def details(ids: list[str], source: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": finding_id,
                "category": source[finding_id].get("category"),
                "source": source[finding_id].get("source"),
                "target": source[finding_id].get("target"),
            }
            for finding_id in ids
            if finding_id in source
        ]

    return {
        "report_reliability": metadata.get("reliability"),
        "report_schema_version": metadata.get("report_schema_version"),
        "trend": trend,
        "new_findings": details(trend["new_ids"], current_by_id),
        "resolved_findings": details(trend["resolved_ids"], baseline_by_id),
        "verdict_boundary": (
            "New, persistent, and resolved describe finding identity across scans, not artifact value or deletion safety."
        ),
    }


def _render_diff(payload: dict[str, Any]) -> str:
    trend = payload["trend"]
    lines = [
        "RepoGC trend diff",
        f"Report reliability: {payload['report_reliability']}",
        f"Baseline present: {trend['baseline_present']}",
        f"Basis changed: {trend['basis_changed']}",
        f"New: {trend['new']}",
        f"Persistent: {trend['persistent']}",
        f"Resolved: {trend['resolved']}",
    ]
    if trend["basis_change_reasons"]:
        lines.append(f"Basis change reasons: {', '.join(trend['basis_change_reasons'])}")
    for title, key in (("New findings", "new_findings"), ("Resolved findings", "resolved_findings")):
        lines.extend(["", title])
        items = payload[key]
        if not items:
            lines.append("- none")
            continue
        for item in items:
            target = f" -> {item['target']}" if item.get("target") else ""
            lines.append(
                f"- {item['id']} {item.get('category')}: {item.get('source')}{target}"
            )
    lines.extend(["", f"Verdict boundary: {payload['verdict_boundary']}"])
    return "\n".join(lines)


def command_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config, config_path = _load(root, args.config)
    self_check = run_self_check()
    repository, git_problem = repository_info(root, config.use_git)
    print(f"Repository: {root}")
    print(f"Config: {config_path or 'built-in defaults'}")
    print(f"Config hash: {config.digest()}")
    print(f"Liveness declarations: {len(config.liveness_declarations)}")
    print(f"Git commit: {repository.get('commit') or 'unavailable'}")
    print(f"Git branch: {repository.get('branch') or 'unavailable'}")
    print(f"Self-check: {'PASS' if self_check.ok else 'FAIL'}")
    for check in self_check.checks:
        print(f"  PASS {check}")
    for failure in self_check.failures:
        print(f"  FAIL {failure}")
    if git_problem:
        print(f"Git note: {git_problem}")
    return 0 if self_check.ok else 2


def _scan_with_trend(root: Path, config: Config) -> tuple[Any, dict[str, Any]]:
    self_check = run_self_check()
    result = scan_repository(root, config, self_check)
    payload = report_payload(result)

    baseline_path = safe_output_path(root, config.baseline)
    try:
        baseline = load_baseline(baseline_path)
        result.trend = compare_baseline(
            payload["findings"],
            baseline,
            scanner_hash=result.scanner_hash,
            config_hash=result.config_hash,
            report_schema=REPORT_SCHEMA_VERSION,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        result.trend = {
            "baseline_present": baseline_path.exists(),
            "basis_changed": True,
            "basis_change_reasons": [f"baseline unavailable: {type(error).__name__}"],
            "new": len(result.findings),
            "persistent": 0,
            "resolved": 0,
            "new_ids": [finding.id for finding in result.findings],
            "persistent_ids": [],
            "resolved_ids": [],
        }
        if result.reliability == "RELIABLE":
            result.reliability = "PARTIAL"
        result.reliability_reasons.append("Formal baseline could not be read safely.")
    payload = report_payload(result)
    return result, payload


def command_scan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config, _ = _load(root, args.config)
    result, payload = _scan_with_trend(root, config)

    markdown_path = args.markdown_out or config.markdown_report
    json_path = args.json_out or config.json_report
    if args.json_stdout:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2 if result.reliability == "UNRELIABLE" else 0
    if not args.no_write:
        write_reports(root, payload, markdown_path, json_path)
    counts = result.category_counts()
    print(
        "RepoGC {status}: broken={broken} orphan={orphan} markers={markers} duplicates={duplicates} unreachable={unreachable}".format(
            status=result.reliability,
            broken=counts["broken_reference"],
            orphan=counts["orphan_candidate"],
            markers=counts["unimplemented_marker"],
            duplicates=counts["duplicate_candidate"],
            unreachable=counts["unreachable_candidate"],
        )
    )
    if args.no_write:
        print("Reports: not written (--no-write)")
    else:
        print(f"Markdown report: {markdown_path}")
        print(f"JSON report: {json_path}")
    if result.reliability_reasons:
        for reason in result.reliability_reasons:
            print(f"NOTICE: {reason}")
    return 2 if result.reliability == "UNRELIABLE" else 0


def command_review(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if args.bundle is not None and (args.report is not None or args.annotations is not None):
        raise ValueError("Evidence bundles require a fresh mechanical scan without imported opinions")
    config, _ = _load(root, args.config)
    if args.report is None:
        result, report = _scan_with_trend(root, config)
    else:
        report = _read_json(safe_output_path(root, args.report))

    annotations = None
    if args.annotations is not None:
        sidecar = _read_json(safe_output_path(root, args.annotations))
        annotations = validate_annotation_sidecar(report, sidecar)
    review = build_review_payload(
        report,
        annotations=annotations,
        limit=args.limit,
    )
    if args.bundle is not None:
        bundle = build_bundle(result, report, config, review)
        write_bundle(root, Path(args.bundle), bundle)
    if args.json:
        print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_review(review))
    if args.bundle is not None:
        print(f"Local evidence bundle: {Path(args.bundle).resolve()}\nBundle SHA-256: {bundle['sha256']}", file=sys.stderr)
    return 0


def command_verify_bundle(args: argparse.Namespace) -> int:
    print(json.dumps(verify_bundle(Path(args.directory), args.expected_sha256), ensure_ascii=False, indent=2))
    return 0


def command_baseline(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config, _ = _load(root, args.config)
    report_path = safe_output_path(root, args.report or config.json_report)
    baseline_path = safe_output_path(root, args.output or config.baseline)
    if not args.update:
        existing = load_baseline(baseline_path)
        if existing is None:
            print(f"No formal baseline at {baseline_path.relative_to(root)}")
            return 0
        print(json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    report = _read_json(report_path)
    baseline = baseline_from_report(report)
    write_baseline(baseline_path, baseline)
    print(f"Formal baseline updated: {baseline_path.relative_to(root)}")
    return 0


def command_explain(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config, _ = _load(root, args.config)
    report_path = safe_output_path(root, args.report or config.json_report)
    report = _read_json(report_path)
    finding = next(
        (item for item in _finding_list(report) if item.get("id") == args.finding_id),
        None,
    )
    if finding is None:
        print(f"Finding not found: {args.finding_id}", file=sys.stderr)
        return 1
    explanation = _explanation_payload(report, finding)
    if args.json:
        print(json.dumps(explanation, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_explanation(explanation))
    return 0


def command_diff(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config, _ = _load(root, args.config)
    report_path = safe_output_path(root, args.report or config.json_report)
    baseline_path = safe_output_path(root, args.baseline or config.baseline)
    report = _read_json(report_path)
    baseline = load_baseline(baseline_path)
    payload = _diff_payload(report, baseline)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_diff(payload))
    return 2 if payload["report_reliability"] == "UNRELIABLE" else 0


def command_annotate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config, _ = _load(root, args.config)
    report_path = safe_output_path(root, args.report or config.json_report)
    if args.input is None:
        if args.output is not None:
            raise ValueError("--output requires --input")
        skipped = {
            "annotation_schema_version": ANNOTATION_SCHEMA_VERSION,
            "status": "skipped",
            "reason": "No annotation input or AI provider is configured.",
            "mechanical_report_modified": False,
        }
        if args.json:
            print(json.dumps(skipped, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("RepoGC annotation skipped: no annotation input or AI provider is configured.")
            print("Mechanical report modified: false")
        return 0

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = root / input_path
    input_path = input_path.resolve()
    if input_path.stat().st_size > MAX_ANNOTATION_INPUT_BYTES:
        raise ValueError(
            f"Annotation input exceeds {MAX_ANNOTATION_INPUT_BYTES} bytes"
        )
    annotation_input = _read_json(input_path)
    report = _read_json(report_path)
    sidecar = validate_annotation_input(report, annotation_input)
    encoded = json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
        return 0

    output_path = safe_output_path(root, args.output)
    if output_path == report_path:
        raise ValueError("Annotation sidecar cannot overwrite the mechanical report")
    if output_path == input_path:
        raise ValueError("Annotation sidecar cannot overwrite its input")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(encoded, encoding="utf-8")
    print(f"Validated annotation sidecar: {output_path.relative_to(root)}")
    print(f"Annotations: {len(sidecar['annotations'])}")
    print("Mechanical report modified: false")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repogc",
        description="Turn repository entropy into a short, read-only human review.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check config, Git metadata, and sentinels.")
    doctor.add_argument("root", nargs="?", default=".")
    doctor.add_argument("--config")
    doctor.set_defaults(handler=command_doctor)

    review = subparsers.add_parser(
        "review",
        help="Show at most five different concerns for a person to check.",
    )
    review.add_argument("root", nargs="?", default=".")
    review.add_argument("--config")
    review.add_argument("--limit", type=int, default=DEFAULT_REVIEW_LIMIT)
    review.add_argument("--json", action="store_true")
    review.add_argument("--bundle", help="Save full local evidence to a new directory outside the target; includes configured source text.")
    review.add_argument("--report", help=argparse.SUPPRESS)
    review.add_argument("--annotations", help=argparse.SUPPRESS)
    review.set_defaults(handler=command_review)

    verify = subparsers.add_parser("verify-bundle", help="Verify a saved local evidence bundle without reading the live repository.")
    verify.add_argument("directory")
    verify.add_argument("--expected-sha256", help="Compare with a digest retained separately by the recipient.")
    verify.set_defaults(handler=command_verify_bundle)

    scan = subparsers.add_parser("scan", help="Run self-checks and the mechanical scan.")
    scan.add_argument("root", nargs="?", default=".")
    scan.add_argument("--config")
    scan.add_argument("--markdown-out")
    scan.add_argument("--json-out")
    scan.add_argument("--no-write", action="store_true", help="Inspect without writing report files.")
    scan.add_argument(
        "--json-stdout",
        action="store_true",
        help="Write the machine report to stdout and do not write files.",
    )
    scan.set_defaults(handler=command_scan)

    baseline = subparsers.add_parser("baseline", help="Inspect or explicitly update the baseline.")
    baseline.add_argument("--root", default=".")
    baseline.add_argument("--config")
    baseline.add_argument("--report")
    baseline.add_argument("--output")
    baseline.add_argument("--update", action="store_true")
    baseline.set_defaults(handler=command_baseline)

    explain = subparsers.add_parser("explain", help="Show complete evidence for one finding.")
    explain.add_argument("finding_id")
    explain.add_argument("--root", default=".")
    explain.add_argument("--config")
    explain.add_argument("--report")
    explain.add_argument("--json", action="store_true", help="Write structured explanation JSON.")
    explain.set_defaults(handler=command_explain)

    diff = subparsers.add_parser("diff", help="Compare a report with the formal baseline.")
    diff.add_argument("--root", default=".")
    diff.add_argument("--config")
    diff.add_argument("--report")
    diff.add_argument("--baseline")
    diff.add_argument("--json", action="store_true", help="Write structured diff JSON.")
    diff.set_defaults(handler=command_diff)

    annotate = subparsers.add_parser(
        "annotate",
        help="Validate an optional AI-background sidecar without changing mechanical evidence.",
    )
    annotate.add_argument("--root", default=".")
    annotate.add_argument("--config")
    annotate.add_argument("--report")
    annotate.add_argument("--input")
    annotate.add_argument("--output")
    annotate.add_argument(
        "--json",
        action="store_true",
        help="Write structured skip status when no input is configured.",
    )
    annotate.set_defaults(handler=command_annotate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"RepoGC error: {error}", file=sys.stderr)
        return 2
