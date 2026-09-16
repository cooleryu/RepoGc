# Decision 0008: review-first product surface

Date: 2026-09-03

## Context

The mechanical engine can expose hundreds of precise Findings, but making raw
categories, schemas, Providers, and sidecars the first user experience obscures
the product question: what deserves a person's attention, and why?

The Best Runtime Box evaluation also showed that orphan and reachability
categories are mechanically distinct while representing one human concern:
whether a reader can find a document from a project entry.

## Decision

Make `repogc review ROOT` the primary product entry.

- Show at most five cards.
- Show at most one representative of each human concern type.
- Map orphan and reachability evidence to one navigation concern.
- Render only `Why`, `Context`, and `Check`, plus one global limitations line.
- Exclude generated artifacts from the default card selection while retaining
  them in the full mechanical report.
- Let the active Codex session add context only for selected evidence through
  the validated sidecar boundary.
- Keep `scan`, schemas, annotations, and baselines as advanced audit surfaces.

## Consequences

The default review is intentionally lossy and cannot replace the full JSON
report for auditing. It changes neither Finding identity nor report Schema 0.7,
so the mechanical baseline does not require a Schema migration. The review page
has an independent 0.1 Schema.

No card is an action verdict. Runtime use, external consumers, human workflows,
and project intent remain unknown until separately observed.
