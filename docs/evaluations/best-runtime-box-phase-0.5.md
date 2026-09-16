# Best Runtime Box Phase 0.5 evaluation

- Date: 2026-09-02
- Corpus alias: `best-runtime-box`
- Observed commit: `ef92a411b9c4044893ad0f320cf22030b4e6e6d4`
- Observed branch: `main`
- Working tree: dirty, with substantial pre-existing user changes

## Evaluation contract

This was a read-only corpus evaluation. RepoGC did not execute target scripts,
install dependencies, write reports into the target, or modify target files.
The corpus configuration excludes dependencies, temporary state, raw harness
runs, and generated local runtime material while retaining source, tests,
skills, and primary harness state.

The Git porcelain-status SHA-256 fingerprint was identical immediately before
and after the final no-write scan. This verifies preservation of the already
dirty target state without recording its private changed-path list.

Reproduction from the RepoGC repository:

```sh
TARGET_REPO=/path/to/best-runtime-box
PYTHONPATH=src python3 -m repogc scan "$TARGET_REPO" \
  --config "$PWD/corpora/best-runtime-box.toml" --no-write
```

The target is intentionally named only by corpus alias in this record. No
machine-local absolute target path is stored.

## Result

| Dimension | Observed value |
|---|---:|
| Execution reliability | `RELIABLE` |
| Scan integrity | `PASS` |
| Coverage | `LIMITED` |
| Scanned files | 138 |
| Existing artifacts represented | 266 |
| Unresolved target nodes | 389 |
| Declared roots | 23 |
| Reachable existing artifacts | 235 |
| Typed edges | 3,172 |
| Wall-clock time after safe duplicate prefilter | about 3 seconds |

Raw finding counts:

| Category | Count |
|---|---:|
| Broken-reference findings | 551 |
| Unimplemented-marker findings | 243 |
| Orphan candidates | 1 |
| Unreachable candidates | 2 |
| Duplicate candidates | 0 |

These raw counts are observations, not an issue count or deletion backlog.
Finding IDs collapse repeated source/target evidence for stable review, while
the graph retains distinct typed evidence edges. Therefore the number of
missing-target edges can exceed the number of broken-reference findings.

## Missing-target evidence matrix

RepoGC observed 1,141 typed edges to missing targets:

| Evidence kind | Missing edges | Default interpretation |
|---|---:|---|
| Test reference | 399 | fixture or simulated path; contextual |
| Fenced-code example | 30 | illustrative layout or snippet; contextual |
| Plain path mention | 712 | unstructured narrative or runtime example; contextual |
| Strong typed edge | 0 | no statically demonstrated operational break |
| Contract-sensitive edge | 0 | no demonstrated broken declared contract |

The source graph contained 128 explicit-extension source-import edges and none
pointed to a missing target. Package/config entry points, declared instruction
contracts, and configured machine-state `artifacts` fields also had no missing
targets.

This is the main Phase 0.5 result: the original `551 broken` headline is
mechanically reproducible but semantically misleading by itself. The typed
layer shows no strong static evidence that the runtime graph is broken.

## Marker boundary at Phase 0.5

At this snapshot, Phase 0.5 still reported 243 case-insensitive lexical marker
findings. They were deliberately excluded from the operational-break
conclusion because token presence did not distinguish product-domain `todo`,
test data, strings, examples, or current commitments.

Phase 0.6 subsequently added deterministic marker context and reduced this
same corpus to 11 marker findings: five review-tier operational-state markers
and six contextual observations. See the dedicated
[Phase 0.6 marker evaluation](best-runtime-box-phase-0.6.md).

## Why finite semantics mattered

The corpus exposed four concrete failure modes in the simpler scanner:

1. Fourteen root `SKILL.md` files were simultaneously called orphans because
   the legacy orphan rule did not share the declared-root model.
2. A suggested `.harness/runs/` directory tree in a fenced code block produced
   apparent contract failures for `status.json`, `result.md`, and
   `observations.json`.
3. Arbitrary strings in JSON task titles were promoted as config references,
   even though only fields such as package entry points or task `artifacts`
   carry declared operational meaning.
4. Pairwise exact similarity on very large harness documents stalled beyond
   90 seconds. A mathematical length upper bound now skips only pairs that
   cannot possibly meet the configured threshold; the same corpus completes
   in about three seconds without changing duplicate semantics.

All four were fixed with deterministic rules and regression tests. No language
model judgment was added to the scanner.

## Remaining review candidates

Two current harness documents are not reachable from declared roots through a
strong typed edge:

- `.harness/skills-runtime-evaluation-completion.md` has no observed inbound
  reference and is also the sole orphan candidate.
- `.harness/skills-runtime-evolution-design.md` is mentioned by narrative
  documents, but those plain mentions are contextual rather than traversable.

Both files are untracked in the observed dirty working tree. Manual inspection
shows purposeful design and completion-checklist content. They are not deletion
candidates. The useful question is whether they should be registered in the
task board, promoted to declared roots, linked through an explicit Markdown
link, committed elsewhere, or intentionally left as local working material.

## Confidence boundary

This evaluation supports these conclusions:

- the configured static source-import graph is closed;
- declared roots and supported strong edge types are mechanically explainable;
- the two document candidates genuinely lack a supported strong route in the
  observed snapshot;
- the target was inspected without executing it.

It does not establish runtime behavior, business value, freshness, ownership,
external consumers, human navigation patterns, or safe deletion. Those remain
`NOT_OBSERVED` or `NOT_INFERRED` coverage dimensions and require project-aware
human review or separately authorized runtime evidence.
