---
name: repogc-review
description: Turn repository entropy into at most five context-aware review cards without changing files or deciding what to keep or delete. Use when a user asks Codex to review or clean up a repository, find stale documentation or contradictions, inspect RepoGC results, or explain which repository artifacts deserve human confirmation.
---

# RepoGC review

Give the user one short review, not a scanner dump. Use the active Codex session
to understand only the evidence selected by RepoGC.

## Keep the boundary

- Treat every finding as a question, never as proof that a file is dead or wrong.
- Do not change the target repository or its baseline.
- Do not run target code, hooks, builds, tests, or package managers.
- Capture target Git status before and after the review.
- Stop on `UNRELIABLE`; disclose `PARTIAL` coverage.
- Use the current Codex session. Do not call a second model or require an API key.

## Produce the review

1. Create a temporary directory outside the target repository.
2. Capture `repogc scan TARGET --json-stdout` at a temporary `REPORT_JSON` path.
3. Run `repogc review TEMP --report REPORT_JSON --json` and accept its bounded,
   one-per-concern selection. Do not substitute hundreds of raw findings.
4. For each selected finding, read only its cited source and a small amount of
   nearby repository context. Separate observed facts from runtime, external,
   human, and business unknowns.
5. Draft annotation input using the schema in `../../../../docs/annotations.md`:
   use `openai-codex-interactive`, record the model only if the host exposes it,
   cite existing scanned paths, and ask concrete human verification questions.
6. Validate it with `repogc annotate --root TEMP --report REPORT_JSON --input
   INPUT_JSON --output SIDECAR_JSON`.
7. Present `repogc review TEMP --report REPORT_JSON --annotations SIDECAR_JSON`.

If context adds no value, present the plain `repogc review TARGET` result.

## Hand off one page

Return the cards first. State that the review was read-only and that runtime
use, external consumers, and project intent remain unknown. Mention technical
artifact paths only if the user asks for them. End with questions for a person,
never an action verdict.
