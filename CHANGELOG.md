# Changelog

All notable project changes will be documented here once versioned releases
begin. The repository currently remains unreleased at version `0.0.0`.

## Unreleased

### Added

- Current-state review onboarding, a reproducible synthetic walkthrough with a
  staged-work counterexample, and a privacy-aware issue feedback template.

- Owner-approved RepoGC public name and Apache-2.0 license, included in packages.
- Deterministic broken-reference, orphan, unfinished-marker, duplicate, and
  unreachable-candidate Findings.
- Historical C1-C6 regressions and graph/marker/liveness sentinels.
- Typed evidence edges, configured Roots, strong-edge reachability, and explicit
  unresolved target nodes.
- Marker lexical context across Python, JavaScript/TypeScript, shell, and
  Markdown.
- Multi-dimensional artifact liveness evidence with explicit unknowns.
- Human-readable and JSON `explain` output.
- Read-only `diff`, explicit `baseline`, `doctor`, and no-write scan modes.
- Schema-versioned JSON and Markdown reports.
- Linux/macOS CI definition and local package-build verification.
- A cross-platform Golden Report projection for Finding, graph, and liveness
  contract stability.
- Explicit human liveness declarations that enrich evidence without suppressing
  Findings or creating hidden Roots.
- A provider-neutral annotation sidecar validator, graceful no-Provider skip,
  provenance binding, and deletion-verdict rejection.
- Codex repository Skills under `.agents/skills` as explicit host-consumed
  graph Roots, protected by sentinel G7.
- A review-first product surface that turns raw signals into at most five
  `Why / Context / Check` cards, one representative per concern kind.
- A repository-scoped `repogc-review` Skill that uses the active Codex session
  to add bounded context without requiring a separate Provider setup.
- Versioned development evaluation cases, source/report snapshots, and a
  separately validated five-dimension AI review record; human outcomes remain
  unmeasured until real trials are run.
- A staged engineering/evaluation protocol and a human trial recording template.
- Explicit local `review --bundle` evidence handoff, full captured text and
  per-Finding selection ledger, with an offline `verify-bundle` reader.

### Fixed

- Git metadata reads disable configured helpers and inherited redirection;
  working-tree status is skipped when content filters are configured or cannot
  be inspected. This hardening is not a general execution sandbox.

- Unrelated preceding prohibitions no longer suppress explicit unchecked
  Markdown tasks from review. Scanner hashes change; formal baselines do not
  update automatically. See decision 0012 and its distinguishing regressions.
- Review wording preserves the distinction between Markdown paths and code
  references, and between unfinished tasks and operational status statements.

### Safety

- Review and scanning remain report-only and offline.
- Embedded AI calls, automatic fixes, deletion, and hosted integrations remain
  unimplemented.
- Apache-2.0 is approved; public release remains pending.
