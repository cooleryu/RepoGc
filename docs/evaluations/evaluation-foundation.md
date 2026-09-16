# Evaluation foundation: first development run

Date: 2026-09-12. Scope: the P0 foundation in the
[engineering and evaluation plan](../ENGINEERING_AND_EVALUATION.md).

This is the retained P0 snapshot. The later
[local handoff evaluation](local-evidence-handoff.md) records production Git
hardening, two wording fixes and complete local evidence retention. Open issues
below describe the original reviewed version, not an assertion that later fixes
never happened.

The evaluation now distinguishes mechanical correctness, AI content review, and
real human outcomes. This run establishes a repeatable development workflow, not
release readiness or completion of the product decision-packet workflow.

## Engineering evidence

| Check | Observed result | Scope |
|---|---|---|
| Project tests | 84 passed | Includes 16 evaluation-tool tests and two new marker-context tests |
| Doctor | 15 sentinels passed | Not the constitution's Gate 0–6 |
| Development suite | 11 cases, 72 declared expectations passed | Synthetic, known development cases; not held out |
| Preserved invariants | 44 checks passed | Per-case sentinels, source bytes, repeated observations and card ID provenance |
| Source distribution | 84 tests and 11 cases passed after extraction | Local macOS/Python 3.12; not remote CI |
| Best Runtime Box | 138 files, 565 Findings, three cards before and after correction | Read-only; target code and tests were not executed |

The same development suite initially failed one case: an unrelated preceding
prohibition suppressed an explicit unfinished task from review. The expectation
was retained. The [four-line classifier correction](../decisions/0012-marker-negation-context.md)
made that case pass while keeping terminology and code-example counterexamples.
The new focused regression also failed on the previous implementation.

The production scanner hash changed from
`3ffbca887821321e662c1590cfdfd9e1f9d1f3cc77beb42fae38c4661c01cc8b` to
`6d1a30f30ad72b12d7a61370656b17ca99372eeb16da50101411359f4f8d89c7`.
Finding identity and report format were not migrated; the formal baseline and
project scan configuration were not updated. Equal BRB counts do not mean the
two scanner versions have identical behavior.

Independent engineering review also exposed four defects in the new evaluation
tool, corrected before handoff: added source files escaping inventory checks;
empty or malformed packets claiming complete coverage; misspelled absence
oracles passing vacuously; and synthetic Git configuration potentially invoking
target-controlled helpers. The runner now rejects these inputs or changes, with
distinguishing regression tests. No malicious target program was executed to
demonstrate the Git risk.

Final document/code reconciliation found a fifth issue: an output error after
publishing the JSON summary could leave a misleading success record. Completion
is now published last, with a late-write-failure regression and an explicit
incomplete record. The development suite does not claim dedicated contract-edge
coverage; existing project regressions cover those graph contracts separately.

## Independent AI review

A separate subagent that did not implement the runner or design the cases read
all eleven source/report/review snapshots. Its task started without inherited
implementation conversation history. It did not read the suite's expected
answers, but case names, review questions and governance documents revealed the
types of risks being tested. This is not a blind, held-out, or cross-model study.
The exact model version is unspecified. AI processing occurred through the
current assistant session/account, not a claimed local-only inference engine;
no additional model provider was installed or invoked by the evaluation CLI.

All 55 case/dimension assessments were completed: 39 `adequate`, 16 `concern`,
zero `not_assessed`. These are rubric judgments, not an accuracy percentage.
The AI record passed the current validator's full-file integrity, case inventory,
line-range and verbatim-citation checks. It reports `record_valid: true` and
`assessment_coverage: complete`, while `judgments_verified` remains `false`.
The main agent also checked the reported concerns against the saved outputs;
the grouped dispositions below remain open product work, not resolved findings.

The separate local AI record and its validation output are named
`foundation-2026-09-12-ai-review.json` and
`foundation-2026-09-12-ai-validation.json` beside the successful bundle.
The original bundle's AI `not_run` field describes collection time; later review
does not overwrite that historical record. Human outcomes remain unmeasured.

## Content issues exposed by the evaluation

The saved review output makes these limitations directly observable:

| Case | Observation | Accepted consequence and next work |
|---|---|---|
| `many-independent-broken-references` | Seven source files have broken links, but only billing appears; its card binds one Finding | P1 must preserve the full evidence; P3 must account for all seven items and deferred work |
| `mutual-links-without-project-entry` | Two connected documents lack a Root entry; only one appears | Grouping must preserve both affected subjects and their relationship |
| `missing-explicit-markdown-target` | A Markdown link is described as a code/configuration reference | Review wording needs an evidence-kind-specific regression before correction |
| `todo-in-current-unchecked-plan` | A current unchecked task is presented as a possibly outdated status note | Distinguish current task evidence from dated status claims; neither proves implementation absence |
| `computed-runtime-consumer` | Source contains a possible computed consumer, while review gives a generic question | P2 should inspect and cite this counterevidence before asking the user; runtime use still remains unknown |
| `same-text-different-contracts` | README describes separate audiences/contracts, while review only asks whether they differ | P2 should surface the actual declarations without treating them as verified runtime or business truth |
| `oversized-configured-document` | Review reports an incomplete-file count but does not name the skipped log or explain its size limit | P1/P3 should surface the concrete coverage gap even when no card is shown |

The omission cases pass their narrow engineering expectations: full reports still
contain the Findings. They do not pass a claim that the card surface accounts for
every important concern. These open issues are retained, not hidden by the green
test count. The mechanical review remains useful as a limited read-only surface;
the full north-star workflow has not been established.

The [real-corpus record](evaluation-foundation-brb.md) adds five contextual cases,
including outdated statements with later source counterevidence and important
same-category items absent from the selected cards. It records input hashes and
the later scan's exact before/after byte inventory, while keeping unobserved
runtime directories and real execution outcomes explicitly unknown.

## Human outcomes and scope

Human outcome status is `not_run`. The
[trial template](../../evals/human-trial-template.json) has no participant results,
no measured time savings, and no completed paired trials. Neither card counts nor
AI estimates substitute for those observations. Cross-model robustness, held-out
generalization, remote CI, publication and Gate 6 are not established here.

The next construction priorities are P1 full evidence handoff, P2 cited
investigation, and P3 independent response items with an explicit deferred list.
P4 compares actual maintenance tasks only after its conditions and thresholds
are frozen. A clean engineering run alone is insufficient to advance a product
value claim.

One security gap needs attention before expanding real-corpus use: production
Git calls do not yet disable configuration-driven helpers. The evaluation
runner's Git rejection fixes its own boundary, not the production wrapper.
Untrusted checkouts must disable Git; see [the security boundary](../../SECURITY.md)
and [privacy limitation](../privacy.md). This was a static code finding, not a
successful exploit test. The repeat BRB audit explicitly disabled helpers for
its Git subprocesses; it does not establish a general scanner guarantee.

## Reproduction and local evidence retention

Run from a source checkout or extracted source distribution:

```sh
PYTHONPATH=src python3.12 -m unittest discover -s tests -p 'test*.py' -q
PYTHONPATH=src python3.12 -m repogc doctor . --config repogc.toml
PYTHONPATH=src python3.12 -m evals.run --output /tmp/repogc-new-evaluation-run
```

Choose a previously nonexistent output directory. The retained successful local
bundle is under `docs/gc_reports/evaluations/foundation-2026-09-12` in this checkout.
Its canonical packet SHA-256 is
`6b9465c9a363211450084c2f2ea8ff43d153a6aebcbe7e3f666eea8dc1e1eb25`.
The earlier failed bundle was retained separately in local temporary storage.
Original bundles are not overwritten by later runs. The successful bundle records
the runner at collection time; subsequent exception-archive handling is separately
covered by the current tests and extracted-source run.

These generated local archives are not included in the public source package and
are not promised permanent retention. A new run uses current code and produces a
new packet; its hash may differ with metadata even when observations agree. The
source package includes the cases, runner, tests, protocol and trial template,
but no copied private BRB source. Users control the retention and disclosure of
their own evaluation evidence.
