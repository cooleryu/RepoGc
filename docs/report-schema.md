# Report Schema 0.7

The JSON report is the machine-readable evidence source. Markdown is a human
view of the same scan and does not replace the JSON contract.

## Top-level fields

| Field | Meaning |
|---|---|
| `metadata` | Version, repository snapshot, hashes, reliability, coverage, and sentinels |
| `summary` | Finding counts by category |
| `evidence_summary` | Typed-edge, role, strength, contract, marker, and liveness rollups |
| `trend` | Baseline presence, basis changes, and new/persistent/resolved identities |
| `findings` | Ordered mechanical Findings and their review subjects |
| `artifact_liveness` | Evidence-availability profiles for Finding subjects |
| `liveness_declarations` | Matched and unmatched human-supplied evidence declarations |
| `artifacts` | Ordered evidence-graph nodes |
| `edges` | Ordered typed evidence-graph edges |

## Determinism and metadata

Finding, Artifact, and Edge collections use deterministic ordering. Finding IDs
do not contain line numbers. `generated_at` may vary between runs and repository
metadata reflects the inspected Git snapshot. Consumers should compare Findings
by ID and must honor `trend.basis_changed` before attributing count changes to
repository quality.

## Reliability and coverage

`metadata.reliability` describes whether the configured execution completed
credibly. `metadata.coverage` separately lists checked, unobserved, and
non-inferred surfaces. A reliable execution is not a claim of semantic
completeness.

## Schema migration

Schema 0.7 recognizes repository-scoped Codex Skills matching
`.agents/skills/**/SKILL.md` as explicit host-consumed Roots. This can remove
orphan and unreachable candidates for those Skill contracts and changes graph
reachability semantics. Comparing with a Schema 0.6 baseline must set
`basis_changed=true`.

Schema 0.6 changed mechanical annotation status from `not_implemented` to
`not_run` and exposed annotation sidecar Schema `0.1`. The provider-neutral
sidecar remains separate and cannot alter the mechanical report. Formal baseline
migration remains an explicit human-reviewed command.
