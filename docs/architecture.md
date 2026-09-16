# Architecture

RepoGC is a local-first, report-only repository entropy observer. Its primary
design constraint is not detection breadth; it is preventing incomplete static
evidence from being presented as a deletion verdict.

## Execution flow

```text
repository + configuration
  -> sentinel self-check
  -> bounded text collection and Git metadata
  -> deterministic detectors
  -> typed evidence graph and configured-root reachability
  -> findings and liveness evidence profiles
  -> one representative card per concern kind (maximum five)
  -> optional bounded Codex context
  -> human review
```

The scanner never runs target-repository builds, hooks, package managers, or
unknown executables. It does not make network requests and does not invoke a
model.

## Boundaries

### Mechanical layer

The mechanical layer owns Finding identity, category, evidence, ordering,
reliability, graph edges, report data, and baseline comparison. For identical
repository content, configuration, and scanner code, these outputs are
deterministic apart from explicit run metadata such as timestamps.

### Evidence graph

Artifacts have a role, existence state, configured-root state, and reachability
path. References retain their syntax, kind, strength, traversability, and
contract sensitivity. Only supported strong edges participate in reachability;
plain mentions, examples, and test references remain visible but do not silently
become production reachability.

### Liveness evidence

Finding subjects receive a bounded profile of observed static evidence and
known unknowns. `NOT_OBSERVED` means only that the configured static surface did
not produce evidence. Dynamic consumers, external systems, runtime access, and
business meaning remain `UNKNOWN` or `NOT_INFERRED` unless a human supplies an
auditable declaration. Declared evidence is labeled `DECLARED`; it does not
create graph edges, change reachability, or suppress Findings.

### Review layer

[The review layer](../src/repogc/review.py) maps raw detector categories to human concern types,
groups by source, chooses at most one representative of each concern, and renders
`Why / Context / Check`. Orphan and reachability evidence intentionally share
one navigation concern. This layer is lossy by design: the complete evidence
remains available through the mechanical
report, while the default product surface stays bounded and readable.

### Optional AI layer

The current provider-neutral sidecar validator can bind externally generated
background to existing Finding IDs and report Artifacts. It does not call a
model, transmit repository content, or merge prose into the mechanical report.
The repository-scoped `repogc-review` Skill lets the active Codex session add
context to the selected cards while the CLI remains deterministic. A future
unattended Provider adapter may explain background and conflicts but cannot
alter mechanical Findings, severity, reliability, trend, or the formal baseline.

## Module map

| Module | Responsibility |
|---|---|
| [`config.py`](../src/repogc/config.py) | Defaults, TOML parsing, validation, configuration hash |
| [`scanner.py`](../src/repogc/scanner.py) | File collection, reference extraction, detectors, reliability |
| [`marker_context.py`](../src/repogc/marker_context.py) | Language-aware lexical marker classification |
| [`graph.py`](../src/repogc/graph.py) | Artifact roles, typed edges, roots, reachability, coverage |
| [`liveness.py`](../src/repogc/liveness.py) | Multi-dimensional evidence availability profiles |
| [`review.py`](../src/repogc/review.py) | Bounded concern selection and human review cards |
| [`git_info.py`](../src/repogc/git_info.py) | Bounded read-only Git background |
| [`baseline.py`](../src/repogc/baseline.py) | Explicit baseline snapshots and deterministic comparison |
| [`reporting.py`](../src/repogc/reporting.py) | Schema payload and Markdown rendering |
| [`self_check.py`](../src/repogc/self_check.py) | Historical and safety sentinels |
| [`cli.py`](../src/repogc/cli.py) | Main `review` entry and lower-level audit commands |

## Reliability model

- `RELIABLE`: all configured files were scanned and sentinels passed.
- `PARTIAL`: the scan ran, but a declared surface such as Git or a file was not
  completely observable.
- `UNRELIABLE`: a sentinel failed. The result is diagnostic only and cannot
  become the formal baseline.

Execution reliability does not mean semantic completeness. Coverage is reported
separately.

## Change control

Finding identity, baseline semantics, reference parsing, self-checks, reliability,
report Schema, and trend meaning are core semantics. Changes require a migration
record, historical regression execution, result comparison, and explicit
baseline migration. Automatic deletion and AI verdicts are outside the current
project constitution.
