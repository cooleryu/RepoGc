# Liveness declaration evaluation: Phase 0.8

- Date: 2026-09-02
- RepoGC report schema: `0.5`
- Mechanical detector change: none
- Finding ID change: none

## Safety fixture

The Golden Report fixture models the historical risk boundary:

- `README.md` reaches `SKILL.md`;
- `SKILL.md` requires `process_log.md`;
- the process log has an unfinished marker;
- a human declaration states that a computed registry path dynamically consumes
  the process log.

The resulting profile labels the dynamic dimension `DECLARED` while retaining
the original marker Finding, typed contract edge, and graph reachability. A
separate G6 sentinel confirms that adding the same kind of declaration to an
unreachable artifact does not make it reachable.

Configuration tests also confirm:

- declaration order does not change the effective configuration hash;
- duplicate declarations canonicalize deterministically;
- absolute POSIX paths, absolute Windows paths, parent traversal, and unknown
  declaration kinds fail closed;
- unmatched declarations remain visible in the report.

## Best Runtime Box no-declaration control

Best Runtime Box was rescanned in read-only mode without inventing any project
knowledge. It has no Phase 0.8 declarations in the corpus configuration.

| Finding category | Phase 0.7 | Phase 0.8 |
|---|---:|---:|
| Broken reference | 551 | 551 |
| Orphan candidate | 1 | 1 |
| Unimplemented marker | 11 | 11 |
| Duplicate candidate | 0 | 0 |
| Unreachable candidate | 2 | 2 |

The Schema 0.5 scan completed as `RELIABLE` in 2.57 seconds and produced the same
441 review-subject liveness profiles. Declaration count was zero. Coverage
reported declaration handling as checked while dynamic, external, and runtime
surfaces remained `NOT_OBSERVED`.

The target working-tree status was identical before and after the scan. RepoGC
wrote no target report or baseline and executed no target code.

## Interpretation

Phase 0.8 creates an auditable channel for repository-specific semantic evidence;
it does not claim that RepoGC independently discovered or verified that evidence.
No Best Runtime Box declaration was added because this evaluation had no
authoritative source for such a claim. This preserves the boundary between
mechanical facts, human declarations, unknowns, and verdicts.
