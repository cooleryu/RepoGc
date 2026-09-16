# Decision 0001: bootstrap RepoGC as an isolated local repository

Status: Accepted
Approval: `[human-approved 2026-09-01]`

## Decision

Create RepoGC in its own local directory and initialize an independent Git
repository. Do not place its implementation in `oss-agent-contrib-radar` or in
any collected third-party checkout.

The working directory name is `repogc`. This is an internal working name, not a
final public naming decision.

## Approved scope

Phase 0 may:

- preserve the project constitution and historical regression cases;
- implement a minimal deterministic, read-only scan core;
- add self-checks and regression tests;
- generate local Markdown and JSON reports;
- create an explicit, reviewable baseline;
- initialize local Git history.

Phase 0 does not approve:

- automatic deletion, movement, rewriting, or repair;
- AI-generated verdicts;
- network calls or repository uploads;
- remote repository creation, publication, or pushes;
- a final project name;
- a license;
- claims that unavailable internal source code was imported or verified.

## Evidence and limitation

The original internal implementation described by the project charter was not
present in the provided workspace. This bootstrap therefore implements the
smallest safety-preserving core from documented behavior. It does not claim
byte-for-byte compatibility with the unavailable scripts.

## Verification

- Run all C1-C6 regression tests.
- Run the sentinel self-check.
- Run RepoGC against its own repository.
- Inspect the generated reports and Git diff.
- Confirm a normal scan does not modify the formal baseline.

## Rollback

The project is isolated in its own directory. Before any remote is configured,
rollback consists of preserving any desired reports and removing or archiving
that single directory. No sibling repository is modified.
