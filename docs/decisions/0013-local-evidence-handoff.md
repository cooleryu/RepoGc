# 0013: Harden Git metadata reads and add local evidence handoff

Date: 2026-09-12. Scope: authorized continuation of the project's priorities.

## Decisions before implementation

First isolate production Git metadata reads from inherited Git redirection and
configuration-driven helpers. Disable fsmonitor, hooks, optional index writes,
automatic maintenance, lazy fetching and transport protocols for these calls.
Use trusted host Git; this is defense in depth, not an OS sandbox for hostile Git
implementations or a filesystem transaction. Test command construction and an
isolated repository configured with a benign helper that must not be invoked.
Also disable configured signature display. Inspect clean/process filter names
before status: if present or inspection fails, skip status and disclose unknown
dirty state with partial reliability rather than invoking content-conversion code.

Add `review --bundle NEW_DIRECTORY` to explicitly save a **local evidence bundle**
outside the target repository. Default review remains unchanged and read-only.
Reject existing destinations and destinations inside the target. Bundle creation
requires a fresh scan; imported reports or AI sidecars are not accepted in v1.
Do not reread source files after scanning: retain the exact decoded UTF-8 text
used by the scan in the in-memory result, without changing the report schema.

The versioned bundle contains the complete report, normalized configuration,
captured source text, existing mechanical cards, and a complete per-Finding
selection ledger. Every Finding is either shown with card IDs or not shown with
an explicit investigation status. Nonselection is not resolution, a deferment
authorized by a person, or a completed prioritization decision. Expose skipped
files and coverage even with zero cards.

`verify-bundle DIRECTORY` validates version, hashes, source/report membership,
configuration binding, source lines, and complete nonoverlapping ledger coverage.
It works without the live target. Invalid bundles are rejected, not executed.
The bundle includes no actions, AI opinions, authorizations or human decisions.
Future protocols must version their additions; unknown fields at this boundary
are rejected. Whole-bundle forgery and semantic truth are outside hash guarantees.

## Acceptance and limits

Tests must distinguish changed/deleted sources, altered reports, omitted ledger
items, invalid versions, path escape, symlinks, overwrite, failed sentinels and
partial coverage. The seven-independent-links case must retain all seven items
even though the current cards select only one. Stored snapshots remain readable
after the original source changes or disappears. No live-source freshness or
runtime use is inferred from successful verification.

This implements P1's initial local handoff substrate, not the full decision
packet, remote receipt, AI investigation, Gate 5 budget, or Gate 6 execution.
Explicit bundle output can include sensitive configured text; it stays local
and must not be uploaded or publicly committed without separate authorization.

No Finding-ID or report-schema migration; new internal captured-source state is
not added to ordinary reports. Scanner hash changes disclose the new basis.
Also correct two independently observed display errors: Markdown references use
neutral path wording rather than code/configuration claims; unfinished tasks are
distinguished from operational status statements, including mixed groups.
These display corrections preserve raw Findings and card selection.
Formal baseline and existing output defaults remain unchanged. Roll back the
new CLI/module/internal capture and Git wrapper separately with their tests;
retain existing evidence and record any reintroduced helper risk.
