# Phase 0.10 Codex Provider evaluation

- Date: 2026-09-03
- Target corpus: Best Runtime Box
- Producer: `openai-codex-interactive`
- Model record: `codex-session-model-unspecified`
- Mechanical report Schema: `0.7`
- Annotation Schema: `0.1`
- Target execution: none
- Target writes: none

## Question

Can the active Codex session supply the optional semantic-background layer while
RepoGC preserves a deterministic mechanical report and refuses action verdicts?

## Procedure

The repository-scoped `repogc-annotate` Skill was initialized with the official
Skill creator and passed its structural validator. The workflow then:

1. captured a Best Runtime Box scan into a temporary report through
   `--json-stdout`;
2. confirmed the report was `RELIABLE` with 565 Findings and no strong
   missing-target edge;
3. selected five Findings spanning contextual path resolution, inbound absence,
   root reachability, and operational-state markers;
4. inspected only four directly relevant repository Artifacts and nearby text;
5. generated an external annotation input in the active Codex session;
6. validated it into a separate temporary sidecar;
7. compared report bytes and target Git status before and after.

## Selected Findings and useful background

| Finding | Mechanical signal | Codex background contribution |
|---|---|---|
| `5e8b2bfc...` | `meta.json` unresolved from `.harness/README.md` | The cited line sits inside a tree-layout example and visually places the file beneath `.harness/runs/run-0001`; the lexical resolver does not interpret indentation as a base path. |
| `98bd198f...` | no inbound reference observed | The file is a dated phase-to-evidence completion checklist containing implementation and test mappings; manual navigation and current workflow membership remain unknown. |
| `d7d86ee0...` | no traversable Root path | The same checklist supplies a structured audit map, while no strong path from the 23 configured Roots was observed. |
| `9a907b66...` | no traversable Root path | The design file defines selector, evolution, evaluation, and implementation architecture; three contextual mentions exist, but those edge kinds are intentionally non-traversable. |
| `1d740809...` | review-tier operational marker | The cited observations entry records a then-current plugin gap; later entries show continued related work, so current completion requires cross-checking newer status and tests. |

These statements add project context and expose ambiguity. They do not direct a
repository action or assign priority, severity, or artifact value.

## Validation results

- Sidecar validation: PASS
- Annotation count: 5
- All annotations `ai_generated=true`: yes
- All annotations `human_verified=false`: yes
- `mechanical_report_modified=false`: yes
- Mechanical report bytes unchanged: yes
- Target Git status unchanged: yes
- Canonical mechanical report SHA-256:
  `63db04cd2238133efd117d0ff87a821005709374c6dd905f681528ed62faa612`

The raw report, draft, and sidecar stayed in a temporary directory and were not
committed. This avoids turning one corpus snapshot into a permanent project
truth source without its complete mechanical report.

## Conclusion

Codex can serve as RepoGC's interactive AI Provider today. The useful division
is not “AI versus no AI”; it is host reasoning versus deterministic validation.
The active agent can interpret selected evidence, while the RepoGC CLI controls
identity, provenance, report binding, forbidden verdict language, and write
boundaries.

This does not establish an unattended service. API automation, scheduling,
credentials, and broader data governance remain separate future decisions.
