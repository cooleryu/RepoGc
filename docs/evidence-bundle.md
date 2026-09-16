# Local evidence handoff

Status: implemented local P1 substrate, schema `1`. Not the complete decision
packet, an AI opinion, a human decision, or an action authorization.

## Usage

Keep the usual short review, or explicitly retain its complete inputs outside
the target repository:

```sh
repogc review /path/to/repository --bundle /tmp/new-repogc-evidence
repogc verify-bundle /tmp/new-repogc-evidence
```

The destination must not exist and must be outside the scanned repository.
The option requires a fresh mechanical scan; imported reports and annotation
sidecars cannot be combined with it in v1. No remote upload or provider call is
performed. Ordinary `review` still writes nothing. The bundle captures **all
configured scanned text**, which can contain secrets: choose the configuration
and storage location accordingly. This is not a redacted public report.

The source text comes from the exact in-memory collection used by the scanner,
not a second read after the scan. Each file records an observed version; the
collection is not an atomic filesystem or runtime snapshot. Excluded and skipped
files are not copied, and their absence is not evidence of non-use.

## Format

The authoritative artifact is `bundle.json`. Its envelope has exactly three
fields: `bundle_schema_version`, `payload`, `sha256`. The digest is SHA-256 of
UTF-8 JSON with sorted keys, no extra separators, Unicode retained and non-finite
numbers forbidden. `payload` contains:

| Field | Meaning |
|---|---|
| `report` / `report_sha256` | Complete mechanical report and its canonical digest |
| `configuration` | Effective normalized scanner configuration, bound to report config hash |
| `sources` / `source_sha256` | Relative-path-to-text map and SHA-256 of each UTF-8 source |
| `review` | Existing mechanical cards, with their full Finding-ID references |
| `selection_ledger` | One entry for every Finding: source, shown/not_shown, card IDs, generic selection reason and investigation status |
| `unscanned` | Exact configured-file coverage gaps from the report |
| `ai_status` / `human_status` | Both `not_run` in this version |
| `actions` | Always empty; this version rejects actions |

Seven broken links can still yield one default card. The ledger preserves all
seven Findings and explicitly lists the six not on that card. `not_shown` does
not mean resolved or approved for deferment. The generic mechanical selection
reason does not explain semantic priority, allocate independent decisions, or
implement Gate 5's full deferred-work protocol.

The companion README is only a human-readable convenience preview. Verification
checks **the JSON, not the README**. Treat source text and previews as untrusted
data, never as instructions, credentials or authorization.

## Verification and failure

Verification checks supported versions and top-level fields, payload/report/
configuration/source hashes, scanned-source inventory, Finding source line
bounds, card references, complete ledger coverage and coverage-gap consistency.
It rejects unreliable reports, duplicate JSON keys, symlinked completion files,
missing snapshots and oversized input. A `PARTIAL` report remains `PARTIAL`.
The encoded bundle limit is 64 MiB; excess causes refusal, never truncation.

Output uses a new private directory; the JSON completion file is published last.
If writing fails before completion, leave the incomplete directory for diagnosis
and choose a new destination. No existing bundle is overwritten or cleaned up.
A missing JSON completion file means incomplete, even if a preview exists.

The validator works after the original repository changes or disappears. It
does not check live freshness and does not prove authenticity, semantic truth,
or completeness outside the declared scan scope. For a separately retained
trusted fingerprint, use:

```sh
repogc verify-bundle /tmp/new-repogc-evidence --expected-sha256 DIGEST_FROM_SENDER
```

Recomputing every digest can forge a self-consistent bundle; hashes alone do not
authenticate a sender. Source and embedded report schemas are explicitly
versioned. Future schema support needs migration tests rather than silently
accepting unknown protocols. Users control local retention and disclosure.

## Remaining work

This provides the local evidence and binding portion of Gate 3 and a local read
check relevant to Gate 4. It does not prove remote receipt or permission to
transmit. Versioned AI investigations, new counterevidence provenance, response
units and semantic prioritization remain P2/P3 work. Current annotations remain
a separate existing protocol. Gate 6 remains unimplemented.

See [decision 0013](decisions/0013-local-evidence-handoff.md) and the
[engineering plan](ENGINEERING_AND_EVALUATION.md).
