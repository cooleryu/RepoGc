# Best Runtime Box Phase 0.6 marker evaluation

- Date: 2026-09-02
- Corpus alias: `best-runtime-box`
- Observed commit: `ef92a411b9c4044893ad0f320cf22030b4e6e6d4`
- Observed branch: `main`
- Working tree: dirty, with substantial pre-existing user changes
- Scan mode: no-write
- Final wall-clock time: 2.63 seconds

The Git porcelain-status SHA-256 fingerprint was identical immediately before
and after the final scan. The evaluation did not change the target's existing
dirty state or record its private changed-path list.

## Outcome

Phase 0.6 reduced the same configured marker surface from 243 raw lexical
findings to 11 exact-token, context-classified findings.

| Evidence kind | Strength | Findings |
|---|---:|---:|
| `operational_state_marker` | review | 5 |
| `marker_term_reference` | contextual | 3 |
| `string_literal_marker` | contextual | 2 |
| `documentation_marker` | contextual | 1 |
| Total | | 11 |

The reduction was not a suppression list. It came from two observable rules:

1. Configured ASCII token `TODO` is case-sensitive and no longer matches the
   ordinary product-domain word `todo` or names such as `todo-runtime`.
2. Each remaining occurrence is classified by artifact role and lexical
   position before it enters the evidence matrix.

## Review tier

All five review-tier findings occur in declared harness-state roots:

- three are in `.harness/observations.md` and explicitly describe incomplete
  plugin, MCP transport, or output-style capability;
- two are in `.harness/plan.md` and explicitly describe incomplete remote MCP
  transport, OAuth, or reconnect behavior.

They are reasonable status-review candidates. RepoGC does not claim they are
current bugs: the large state documents may contain historical sections, and
runtime or issue-tracker evidence was not observed.

## Contextual tier

- Three `.harness/README.md` occurrences sit under rules that say not to record
  temporary or product-code TODO lists there. They are marker terminology, not
  pending work.
- Two `src/providers/demo.js` occurrences are inside strings used to demonstrate
  or select a search pattern.
- One `.harness/pitfalls.md` occurrence explains the correct state for a
  capability that is not implemented; it is not in a declared operational
  root.

No review-tier result came from a test, generated artifact, source string,
lowercase product-domain term, fenced example, or inline-code example.

## Confidence boundary

This evaluation establishes lexical context for the configured static files.
It does not establish whether the five status statements are fresh, scheduled,
owned, important, or already resolved elsewhere. The next evidence source for
those questions should be runtime traces, task/issue state, or explicit human
review—not a language-model guess over the repository.
