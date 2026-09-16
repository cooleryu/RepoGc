# Best Runtime Box evaluation: Phase 0.7 liveness review

- Date: 2026-09-02
- RepoGC report schema: `0.4`
- Target: local Best Runtime Box checkout
- Mode: read-only; target scripts were not executed
- Corpus config: `corpora/best-runtime-box.toml`

## Question

Can RepoGC show enough project-aware evidence to support human review without
claiming that static engineering checks understand the repository's complete
business or runtime semantics?

## Result

The scan completed as `RELIABLE` in 2.52 seconds:

| Finding category | Count |
|---|---:|
| Broken reference | 551 |
| Orphan candidate | 1 |
| Unimplemented marker | 11 |
| Duplicate candidate | 0 |
| Unreachable candidate | 2 |

The counts match the Phase 0.6 mechanical scan. Phase 0.7 does not change the
detectors or Finding IDs; it adds review context. Shared review subjects produced
441 bounded artifact-liveness profiles.

## Representative review subject

One review-tier Finding came from `.harness/observations.md`:

```text
- 当前只实现 local plugin manifest,未实现 marketplace/cache/install/update。
```

RepoGC classified it as `operational_state_marker` and showed the containing
artifact with:

| Dimension | Result |
|---|---|
| Human-declared root | `OBSERVED` |
| Reachable from configured root | `OBSERVED` |
| Static inbound references | `OBSERVED` |
| Contract or instruction consumer | `OBSERVED` |
| Build, test, CI, state, or config consumer | `OBSERVED` |
| Git last touch | `OBSERVED` |
| Dynamic consumers | `UNKNOWN` |
| External-system consumers | `UNKNOWN` |
| Runtime access | `UNKNOWN` |
| Business meaning | `NOT_INFERRED` |

The artifact had seven strong inbound edges, five contextual inbound edges, and
five contract-sensitive inbound edges. This is materially different from
reporting the marker alone: a reviewer can see that the state file participates
in declared project mechanisms, while RepoGC still refuses to invent runtime or
business evidence.

## Safety observations

- The target working-tree status was identical before and after the scan.
- RepoGC wrote no reports or baseline into the target repository.
- No target-repository script, hook, build, install, or test was executed.
- No network or AI provider was used.
- `NOT_OBSERVED` was not converted into an absence or deletion verdict.

## Interpretation

Phase 0.7 closes a review-workflow gap, not semantic completeness. It demonstrates
that explicit repository contracts, roots, typed static edges, Git context, and
unknown surfaces can coexist in one explanation. It does not establish that all
551 unresolved references are defects, nor that the orphan or unreachable
candidates lack dynamic, external, human, or business consumers.
