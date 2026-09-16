# Phase 0.9 annotation-sidecar evaluation

- Date: 2026-09-03
- Mechanical report Schema: `0.6`
- Annotation Schema: `0.1`
- Provider calls: none
- Network calls: none

## Question

Can RepoGC accept optional AI-generated background without letting generated
text alter mechanical evidence or become a deletion, retention, or value
verdict?

## Results

The no-input path returned an explicit skipped status, exited successfully, and
wrote no files. A valid fixture produced a separate sidecar bound to the report
Schema, repository Commit, scanner hash, configuration hash, and reliability.
The source report remained byte-for-byte unchanged. The sidecar included a
SHA-256 binding to the complete canonical JSON report payload.

Validation rejected:

- unknown or duplicate Finding IDs;
- evidence paths that were not existing, scanned Artifacts;
- unsupported top-level or annotation fields;
- incompatible report Schemas and duplicate report Finding IDs;
- `UNRELIABLE` reports;
- inputs larger than 1,000,000 bytes;
- conservative English and Chinese deletion, removal, retention, and value
  vocabulary.

The complete local suite passed 57 tests. `repogc doctor` passed 14 safety
sentinels, including the annotation/mechanical boundary and verdict rejection.

## Complex-corpus regression

The Best Runtime Box corpus was rescanned through `--no-write` after the Schema
0.6 change:

| Signal | Count |
|---|---:|
| Broken-reference candidates | 551 |
| Orphan candidates | 1 |
| Marker candidates | 11 |
| Duplicate candidates | 0 |
| Unreachable candidates | 2 |

The result was `RELIABLE`; the target repository's already-dirty Git status had
149 entries before and after and was byte-for-byte identical as status text.
RepoGC did not run target code and did not send target content to a model.

## Boundary conclusion

This phase proves a strict import/validation seam, not the quality or privacy of
any model provider. A provider integration remains blocked on a separate human
decision covering data selection, transmission, retention, disabling, and
offline behavior. Mechanical RepoGC remains complete without that integration.
