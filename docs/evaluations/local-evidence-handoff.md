# Local evidence handoff: implementation evaluation

Date: 2026-09-12. Scope: [decision 0013](../decisions/0013-local-evidence-handoff.md).

## Result

The production CLI can now save a complete **local mechanical evidence bundle**
outside its target, and verify it later without that target. This implements the
initial P1 substrate, not the complete AI investigation/decision workflow.

- 97 project tests passed, including new Git guards, bundle failure paths and
  review-wording regressions.
- 15 doctor sentinels passed; the 11-case development suite passed again.
- The source distribution built and installed offline into a temporary virtual
  environment. From outside the source checkout, the installed CLI verified the
  real bundle with its separately supplied digest, then created and verified a
  new bundle for the seven-independent-links fixture.
- No baseline update, public publication, target cleanup or runtime execution
  was performed. Test fixture commits and baseline writes were confined to
  temporary test repositories.

## Real development corpus

Best Runtime Box was scanned with the existing corpus configuration, using the
new production Git wrapper. The bundle retained 138 scanned source texts and
565 Findings. Its three cards referenced eight Findings; the ledger explicitly
accounted for the other **557 not shown**. These are mechanical Findings, not
557 independent business problems, decisions, or approved deferrals.

The report remained `RELIABLE`, with no skipped configured files. Immediately
after collection, every retained source digest matched that source's current
bytes in the live checkout. This check covers the 138 captured texts, not
excluded directories, an atomic repository snapshot, or target runtime behavior.

The retained bundle is in local temporary storage; its machine-specific path is omitted.

- Canonical bundle digest: `2b973263b8c48856a1f0248d385072f3437b21d70b15a00c81d52dc850911320`.
- Scanner hash: `582bb44899152e0fb6f46f719313246d2213e36af3af23ec1e6497820ab2466d`.
- Encoded JSON size: 8,139,500 bytes.

The local archive includes private corpus text and is **not** included in the
public source package. Its lifetime is user-controlled and temporary storage is
not promised permanent retention. Re-running creates a new evidence version.

## Distinguishing tests

The new Git command-construction test failed before implementation. The final
wrapper strips inherited Git redirection and disables fsmonitor, hooks,
signature display, optional index writes, maintenance and transports. A real
temporary repository configured with a benign fsmonitor helper did not invoke
it; its index bytes and modification time remained unchanged. A configured
clean filter caused status to be skipped and dirty state to remain unknown.
This hardening assumes trusted Git and stable inputs, not an OS sandbox.

The bundle suite verifies all seven Findings survive a one-card surface, stored
source survives later live edits, omitted source/ledger entries and wrong
digests are refused, partial coverage stays partial, unreliable scans fail,
existing destinations are not overwritten, targets cannot contain the output,
symlink completion files and unknown versions are refused, and publication
failure leaves no valid completion artifact. Configured text is captured inside
the original scan, not reread afterward.

Two previous content-review observations were corrected with focused regressions:
Markdown paths no longer become code/configuration claims, and unfinished-work
markers are distinguished from operational status statements. This does not
infer whether a task is actually unfinished or a status statement actually stale.

## Remaining acceptance work

No new independent AI review or human trial was performed for this implementation
round; earlier AI reviews describe their original bound snapshots and are not
relabelled as validation of this version. The earlier cases informed the fixes.

The default cards still prioritize only representatives. The optional bundle
provides a complete ledger, but not semantic grouping, independent human
response units, investigation ownership or a full deferred-work protocol.
P2 must add evidence-cited AI investigations and revalidation; P3 must account
for actual human attention; P4 must test real maintenance outcomes. Gate 6 and
automatic cleanup remain outside the implemented product.

The [bundle contract](../evidence-bundle.md) specifies format, privacy and
verification limits. `bundle_valid` is structural consistency, never truth,
freshness, remote receipt, human consent or permission to execute.
