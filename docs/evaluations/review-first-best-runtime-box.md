# Review-first evaluation: Best Runtime Box

Date: 2026-09-03

## Question

Can RepoGC turn a large, dirty, AI-heavy repository into one understandable
review page without modifying the target or pretending to know its full intent?

## Boundary

- Target: a local Best Runtime Box checkout (personal path omitted)
- Observed commit: `ef92a411b9c4044893ad0f320cf22030b4e6e6d4`
- Initial working tree: dirty, 148 porcelain status entries
- Configuration: `corpora/best-runtime-box.toml`
- Target execution: none
- Target writes: none

Runtime directories `.tmp`, `.brb`, and `.harness/runs` were excluded by the
declared corpus configuration. This is a scoped repository review, not a claim
about unconfigured content.

## Mechanical result

The reliable scan read 138 files and produced 565 Findings:

| Category | Count |
|---|---:|
| Broken reference | 551 |
| Unimplemented or status marker | 11 |
| Unreachable candidate | 2 |
| Orphan candidate | 1 |
| Duplicate candidate | 0 |

The review layer mapped these Findings to three human concerns rather than
showing repeated detector categories:

1. a status log whose three point-in-time statements need comparison with later
   work;
2. a completion checklist with no observed incoming project navigation;
3. paths inside a directory-tree example that the lexical resolver interpreted
   from a different base directory.

## Context result

The active Codex session inspected only the selected evidence. It observed later
source and test evidence for local marketplace install, signed update/rollback,
and the interactive output-style command, while remote registry and part of the
remote transport lifecycle remain described as open work.

Three annotations passed the deterministic sidecar validator. The mechanical
report SHA-256 before and after validation remained
`5621f0d466ad5f3ac4f52dfc002b487de0ccff8711ac72e54c6e9ecc0493fa26`.
The sidecar bound the canonical report payload as
`bbc558aa79f4e8ba673f76fc3f0cdf642d93a3ace0fe5b1bd1e1e21300a35564`.

## Outcome

RepoGC reduced 565 raw Findings to three distinct review cards with one next
question each. A before/after porcelain comparison confirmed all 148 pre-existing
target status entries were unchanged.

This supports the narrow claim that the review-first surface makes the selected
static evidence understandable. It does not establish runtime use, external
consumers, project intent, or an action decision.
