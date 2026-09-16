# Privacy and local execution

RepoGC's current mechanical scanner is local-first and offline by default.

## Data read

RepoGC reads configured text files, file metadata, its configuration, and a
bounded set of Git metadata. Git access uses read-only commands for repository
identity, working-tree state, and last-touch commit/date background.

Git reads disable helper and transport entry points and inherited Git redirection.
Configured content filters cause working-tree status to be skipped, keeping dirty
state unknown and scan reliability partial. This is not a general sandbox; use
`[scan] use_git = false` when Git background is unnecessary for an untrusted
checkout. The synthetic evaluation runner requires that setting.

## Data written

A normal scan may write only the configured Markdown report and JSON report.
The formal baseline changes only after an explicit `repogc baseline --update`.
`review`, `scan --no-write`, `scan --json-stdout`, `doctor`, `explain`, and
`diff` do not write repository reports or baselines. `annotate` writes only when
both a valid input and an explicit repository-relative sidecar output are
supplied.

Explicit `review --bundle` additionally writes complete captured source text and
mechanical evidence to a new directory outside the target repository. This may
include sensitive text and is not a public/redacted artifact. `verify-bundle`
reads the saved JSON without accessing the original repository. See the
[bundle contract](evidence-bundle.md) for retention and verification limits.

RepoGC never deletes, moves, renames, or rewrites candidate artifacts.

## Data not collected or transmitted by the mechanical CLI

The RepoGC CLI does not:

- make network requests;
- upload repository content;
- invoke an AI provider;
- collect runtime file-access events;
- query external systems;
- run target-repository scripts, hooks, builds, or package managers;
- include Git author names or email addresses in reports;
- write absolute repository paths into public report payloads.

The code-execution boundary assumes trusted host tools and stable filesystem
inputs; configuration guards are not an operating-system sandbox.

## Optional AI status

A provider-neutral sidecar validator and the `repogc-review` Codex workflow are
implemented; no model or network call is embedded in the RepoGC CLI. Selected
report fields and evidence excerpts read by Codex are processed under the active
Codex workspace/account controls and must not be described as local-only. Before
any unattended Provider integration, the project must document exactly which
snippets leave the machine, the Provider, retention
behavior, opt-out controls, and an offline-only path. AI output remains visibly
separate and cannot alter mechanical evidence or verdicts.
