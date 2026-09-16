# 0012: Keep explicit tasks independent of preceding negation

Date: 2026-09-12.
Status: implementation and regression tests within the authorized evaluation work.

## Problem and evidence

The development case `repository-text-is-not-authorization` retained a raw
unfinished marker but produced no review card. The Markdown classifier searched
five lines for any negation and treated the following unchecked task as marker
terminology. An earlier sentence asking the reader not to report findings was
enough to downgrade an unrelated recovery task.

The same failure occurs with ordinary guidance such as “Do not commit
credentials.” Changing only that preceding sentence changed whether the task
appeared in the default review. The case expectation is retained; the document
does not establish that the recovery task is merely an example.

## Decision and behavior

An explicit unchecked Markdown task does not inherit the preceding negation
window's terminology classification. Fenced examples and inline code retain
priority. Existing negated terminology lists and other contextual marker rules
remain in place; this change does not remove negation handling globally.

Before: unrelated preceding negation could turn an unchecked task into
`marker_term_reference / contextual`, omitting it from default review.

After: the task remains `unchecked_task_marker / review`, unless an earlier
lexical rule identifies an example or another applicable context. Raw evidence
is still preserved. Review eligibility is not proof that the work is unfinished,
important, or authorized, and repository text is never execution authorization.

This is a bounded precedence correction, not a general natural-language
negation parser or evidence that an external model resists prompt injection.

## Verification and migration

New regression cases place the same unchecked task after ordinary safety
guidance, an unrelated prohibition, an injected suppression request, and a
negated terminology list. They assert both its mechanical classification and
its presence in default review. These cases fail on the previous classifier.

Separate counterexamples retain contextual classifications for a genuine
negated terminology list, quoted terminology, inline code and fenced examples,
including task-shaped example text. Existing marker-context tests continue to
cover source strings, comments, test/generated roles and contract sensitivity.

Verification: run `python3.12 -m unittest discover -s tests -p
'test_marker_context.py'` with `PYTHONPATH=src`, then rerun the fixed development
suite and the project checks. Suite passing is only mechanical evidence; the AI
review questions remain a separate assessment.

The focused run before the fix failed all four unrelated-negation subcases;
after the fix, all nine marker-context tests passed, including the contextual
counterexamples. This records a distinguishing regression, not just a new test
that also passed with the old implementation.

No report-format or Finding-ID migration is needed. Existing marker evidence
keeps its identity, while classification, review eligibility and the scanner
hash change. Comparisons across scanner versions must disclose the changed
measurement basis; they are not evidence of repository cleanup. This change
does not update the formal baseline or alter write permissions.

## Rollback

Revert the explicit-task exception and its new regression cases together,
recording that this restores the known suppression defect. Keep the development
case and its expectation unchanged so the failure remains visible. No repository
content, formal baseline or authorization state requires restoration.
