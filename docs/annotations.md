# Optional annotation sidecar

This is an advanced engine protocol. Normal users should run `repogc review` or
invoke `$repogc-review`; they do not need to construct a sidecar themselves.

RepoGC does not contain a built-in model Provider. The annotation command is a
strict import and validation boundary for background generated elsewhere. The
mechanical scanner remains fully usable without a model, network, or API key.

## No-provider behavior

```sh
repogc annotate --root .
```

This prints an explicit skipped status, exits successfully, and writes nothing.

## Input format

```json
{
  "provider": "provider-name",
  "model": "model-name",
  "data_handling": "Describe what was transmitted and retained.",
  "annotations": [
    {
      "finding_id": "existing-finding-id",
      "observed_background": "Current evidence shows ...",
      "evidence_sources": ["docs/example.md"],
      "uncertainties": ["Runtime use has not been observed."],
      "human_checks": ["Confirm the active delivery contract."]
    }
  ]
}
```

All evidence paths must identify existing, scanned Artifacts in the mechanical
report. This prevents generated text from inventing repository sources or citing
an unresolved target as if its contents had been inspected. Annotation input is
limited to 1,000,000 bytes.

## Validate to stdout

```sh
repogc annotate --root . \
  --report docs/gc_reports/latest.json \
  --input annotation-input.json
```

## Write a separate sidecar

```sh
repogc annotate --root . \
  --report docs/gc_reports/latest.json \
  --input annotation-input.json \
  --output docs/gc_reports/annotations.json
```

The output path must remain inside the repository and cannot overwrite the
mechanical report or input. The sidecar binds itself to the current report
Schema, a SHA-256 of the complete canonical JSON report payload, repository
Commit, scanner hash, configuration hash, and reliability. Unsupported report
Schemas and duplicate report Finding IDs are rejected.

## Safety boundary

Every output annotation is explicitly AI-generated and not human verified.
Deletion, removal, retention, value, priority, severity, Root, and baseline
decisions stay outside the annotation protocol. Conservative verdict vocabulary
is rejected automatically in both English and Chinese, even when it appears in
an otherwise valid background or human-check field.

Any unattended Provider API and any processing outside the active host workflow
remain separate future decisions. Every producer is responsible for recording
truthful provider, model, and data-handling provenance in the input.

## Codex as the interactive Provider

A source checkout includes `.agents/skills/repogc-review`. When invoked in
Codex, the active session can inspect selected mechanical Findings and their
cited Artifacts, draft annotation input, and run this validator. Use
`provider=openai-codex-interactive`; record the host model only when it is
actually exposed, and describe active-session data handling without claiming
that processing stayed local.

This is a host-provided interactive workflow, not a model call embedded in the
RepoGC CLI. The Skill defaults to temporary artifacts, at most five concern
types, no target execution, and no target-repository writes.
