from __future__ import annotations

from repogc import REPORT_SCHEMA_VERSION
from repogc.annotations import validate_annotation_input
from repogc.baseline import compare_baseline
from repogc.config import Config
from repogc.graph import build_evidence_graph
from repogc.liveness import build_liveness_profiles
from repogc.marker_context import MarkerHit, classify_marker_hits
from repogc.models import SelfCheckResult
from repogc.scanner import compute_inbound, extract_references, stable_id


def run_self_check() -> SelfCheckResult:
    passed: list[str] = []
    failures: list[str] = []

    def check(name: str, condition: bool) -> None:
        if condition:
            passed.append(name)
        else:
            failures.append(name)

    known_c1 = {"README.md", "tools/guarded_push.py"}
    c1 = extract_references(
        "README.md",
        "没有 .gitlab-ci.yml，tools/guarded_push.py 只是门禁包装",
        known_c1,
    )
    check("C1 token-scoped negation", [reference.raw for reference in c1] == ["tools/guarded_push.py"])

    known_c2 = {"core_principles_memo.md", "provenance_seal_mechanism.md"}
    c2_references = extract_references(
        "core_principles_memo.md",
        "See provenance_seal_mechanism.md",
        known_c2,
    ) + extract_references(
        "provenance_seal_mechanism.md",
        "See core_principles_memo.md",
        known_c2,
    )
    c2_inbound = compute_inbound(c2_references, known_c2)
    check("C2 mutual document references", all(c2_inbound[path] for path in known_c2))

    before = stable_id("SKILL.md", "TODO preserve this contract")
    after = stable_id("SKILL.md", "TODO preserve this contract")
    check("C3 line-independent stable ID", before == after)

    c4 = extract_references("README.md", "Read example.jsonl", {"README.md"})
    check("C4 JSONL suffix preservation", len(c4) == 1 and c4[0].raw == "example.jsonl")

    c5 = compare_baseline(
        [],
        {
            "scanner_hash": "old",
            "config_hash": "same",
            "report_schema_version": REPORT_SCHEMA_VERSION,
            "findings": [],
        },
        scanner_hash="new",
        config_hash="same",
        report_schema=REPORT_SCHEMA_VERSION,
    )
    check("C5 basis-change disclosure", c5["basis_changed"] is True)

    known_c6 = {"SKILL.md", "process_log.md"}
    c6_references = extract_references(
        "SKILL.md",
        "Required delivery artifact: process_log.md",
        known_c6,
    )
    c6_inbound = compute_inbound(c6_references, known_c6)
    check("C6 contract consumer reference", c6_inbound["process_log.md"] == {"SKILL.md"})

    graph_config = Config(
        graph_root_globs=("SKILL.md",),
        contract_globs=("SKILL.md",),
        instruction_globs=("SKILL.md",),
        use_git=False,
    )
    graph_contents = {
        "SKILL.md": "Required delivery artifact: process_log.md",
        "process_log.md": "Execution evidence",
    }
    graph_references = extract_references(
        "SKILL.md",
        graph_contents["SKILL.md"],
        set(graph_contents),
    )
    graph_artifacts, graph_edges = build_evidence_graph(
        graph_contents,
        graph_references,
        set(graph_contents),
        graph_config,
    )
    process_artifact = next(
        artifact for artifact in graph_artifacts if artifact.path == "process_log.md"
    )
    check(
        "G1 declared contract reachability",
        process_artifact.reachable
        and len(graph_edges) == 1
        and graph_edges[0].kind == "declared_contract_reference",
    )

    mention_config = Config(graph_root_globs=("README.md",), use_git=False)
    mention_contents = {
        "README.md": "Historical note: process_log.md",
        "process_log.md": "Execution evidence",
    }
    mention_references = extract_references(
        "README.md",
        mention_contents["README.md"],
        set(mention_contents),
    )
    mention_artifacts, mention_edges = build_evidence_graph(
        mention_contents,
        mention_references,
        set(mention_contents),
        mention_config,
    )
    mentioned_artifact = next(
        artifact for artifact in mention_artifacts if artifact.path == "process_log.md"
    )
    check(
        "G2 plain mentions are contextual",
        not mentioned_artifact.reachable
        and len(mention_edges) == 1
        and mention_edges[0].kind == "path_mention"
        and not mention_edges[0].traversable,
    )

    marker_source = '# TODO active\nlabel = "TODO example"\n'
    marker_hits = [
        MarkerHit(line=1, column=2, line_text="# TODO active", token="TODO"),
        MarkerHit(
            line=2,
            column=9,
            line_text='label = "TODO example"',
            token="TODO",
        ),
    ]
    marker_contexts = classify_marker_hits(
        "fixture.py",
        marker_source,
        "source",
        marker_hits,
        contract_source=False,
        operational_source=False,
    )
    check(
        "G3 source-comment marker review tier",
        marker_contexts[marker_hits[0]].kind == "source_comment_marker"
        and marker_contexts[marker_hits[0]].strength == "review",
    )
    check(
        "G4 string marker contextual tier",
        marker_contexts[marker_hits[1]].kind == "string_literal_marker"
        and marker_contexts[marker_hits[1]].strength == "contextual",
    )

    liveness = build_liveness_profiles(
        graph_artifacts,
        graph_edges,
        ("process_log.md",),
    )[0]
    check(
        "G5 liveness unknowns remain explicit",
        liveness["dimensions"]["contract_or_instruction_consumer"]["status"]
        == "OBSERVED"
        and liveness["dimensions"]["dynamic_consumers"]["status"] == "UNKNOWN"
        and liveness["dimensions"]["business_meaning"]["status"]
        == "NOT_INFERRED",
    )

    declared_liveness = build_liveness_profiles(
        mention_artifacts,
        mention_edges,
        ("process_log.md",),
        declarations=(
            {
                "path": "process_log.md",
                "kind": "dynamic_consumer",
                "source": "fixture registry",
                "reason": "Loaded through a computed case path.",
            },
        ),
    )[0]
    check(
        "G6 declarations do not create hidden reachability",
        not mentioned_artifact.reachable
        and declared_liveness["dimensions"]["dynamic_consumers"]["status"]
        == "DECLARED"
        and declared_liveness["dimensions"]["root_reachability"]["status"]
        == "NOT_OBSERVED",
    )

    codex_skill_path = ".agents/skills/review/SKILL.md"
    codex_skill_artifacts, _ = build_evidence_graph(
        {codex_skill_path: "# Review workflow"},
        [],
        {codex_skill_path},
        Config(use_git=False),
    )
    codex_skill = codex_skill_artifacts[0]
    check(
        "G7 repo-scoped Codex Skill host root",
        codex_skill.root
        and codex_skill.reachable
        and codex_skill.reachable_from == codex_skill_path,
    )

    annotation_report = {
        "metadata": {
            "reliability": "RELIABLE",
            "report_schema_version": REPORT_SCHEMA_VERSION,
            "repository": {"commit": "fixture"},
            "scanner_hash": "fixture",
            "config_hash": "fixture",
        },
        "findings": [{"id": "fixture-finding"}],
        "artifacts": [{"path": "README.md", "exists": True, "scanned": True}],
    }
    annotation_input = {
        "provider": "fixture",
        "model": "fixture",
        "data_handling": "local fixture",
        "annotations": [
            {
                "finding_id": "fixture-finding",
                "observed_background": "Current evidence shows a repository marker.",
                "evidence_sources": ["README.md"],
                "uncertainties": ["Runtime intent is unknown."],
                "human_checks": ["Confirm the current contract."],
            }
        ],
    }
    annotation_sidecar = validate_annotation_input(annotation_report, annotation_input)
    check(
        "A1 annotation sidecar preserves mechanical boundary",
        annotation_sidecar["mechanical_report_modified"] is False
        and annotation_sidecar["annotations"][0]["finding_id"]
        == "fixture-finding",
    )
    unsafe_input = {
        **annotation_input,
        "annotations": [
            {
                **annotation_input["annotations"][0],
                "observed_background": "This file is safe to delete.",
            }
        ],
    }
    try:
        validate_annotation_input(annotation_report, unsafe_input)
    except ValueError:
        verdict_rejected = True
    else:
        verdict_rejected = False
    check("A2 annotation deletion verdict rejection", verdict_rejected)

    return SelfCheckResult(
        ok=not failures,
        checks=tuple(passed),
        failures=tuple(failures),
    )
