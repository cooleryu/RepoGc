# Evaluation foundation: Best Runtime Box

Date: 2026-09-12. Read-only source review and scans before and after the marker
context correction made during this evaluation work.

This is a development corpus already used in earlier RepoGC evaluations, not a
held-out repository. The observations below inform test cases and review criteria;
they do not estimate generalization, model accuracy, user time saved, or release
readiness. No target program, test, installer, hook, or model provider was executed.

## Input and reproducibility

- Local target: a Best Runtime Box checkout (personal path omitted).
- Observed HEAD: `ef92a411b9c4044893ad0f320cf22030b4e6e6d4`, branch `main`.
- The working tree was dirty. HEAD alone does not identify the reviewed contents.
- Configuration: [corpus configuration](../../corpora/best-runtime-box.toml).
- Configuration file SHA-256: `b88cd528e130e8f3ce9c42345f52ad08cd5fcfe4aa5f4e096d8e5eeed7aec016`.
- Normalized configuration hash: `c201ad3258cc972c6d7f77396ea2781c672a4dde3a2c66363ec86f7d778dc3ee`.
- Before-correction scanner hash: `3ffbca887821321e662c1590cfdfd9e1f9d1f3cc77beb42fae38c4661c01cc8b`.
- After-correction scanner hash: `6d1a30f30ad72b12d7a61370656b17ca99372eeb16da50101411359f4f8d89c7`.
- Report schema: `0.7`.

Run from the RepoGC checkout with Python 3.11+:

```sh
PYTHONPATH=src python3.12 -m repogc scan \
  /path/to/best-runtime-box \
  --config corpora/best-runtime-box.toml \
  --json-stdout

PYTHONPATH=src python3.12 -m repogc review \
  /path/to/best-runtime-box \
  --config corpora/best-runtime-box.toml \
  --json
```

These commands write to stdout and do not create target reports or a baseline.
They re-scan the current checkout; they cannot reconstruct an earlier dirty state.
The one-off audit retained its script, full report, review JSON, and summary in the
local temporary directory (machine-specific path omitted). This temporary
directory is not a permanent public evidence archive or a third-party source copy
shipped with RepoGC.

The repeat audit used the separate directory
a separate local temporary location, preserving the earlier output. It retained
the new report, review, summary, before/after comparison, and two source-hash
inventories. It disabled Git fsmonitor and hooks for its read-only Git subprocesses.
The source inventories contain relative paths and SHA-256 values, not copies of
the target source files.

Runtime directories `.brb`, `.harness/runs`, and `.tmp` were excluded by the corpus
configuration. Their settings, traces, and runtime artifacts remain unobserved.

## Mechanical observations before and after correction

| Measurement | Observed value |
|---|---:|
| Configured text files read | 138 |
| Skipped configured files | 0 |
| Graph nodes, including referenced targets | 655 |
| Typed edges | 3,172 |
| Artifact liveness profiles | 441 |
| Broken-reference Findings | 551 |
| Marker Findings | 11 |
| Unreachable Findings | 2 |
| Orphan Findings | 1 |
| Duplicate Findings | 0 |
| Total Findings | 565 |
| Signals admitted to default review selection | 302 |
| Signals excluded from default selection | 263 |
| Candidate source/category groups | 20 |
| Groups shown as cards | 3 |

The scan reported `RELIABLE` with no reliability reasons and took approximately
2.69 seconds. The 263 excluded signals are distinct from admitted signals whose
groups were not selected. Three cards do not mean three human authorization
decisions or that all other concerns have been resolved.

The table above applies to both freshly measured scans: every listed count was
unchanged after the marker-context correction. Both completed as `RELIABLE` in
approximately 2.69 seconds. Comparing Finding IDs found zero additions and zero
removals. The retained comparison records the two different scanner hashes, rather
than treating equal counts as proof of equal scanner behavior. The correction's
synthetic regression case provides different evidence from this unchanged corpus.

Git status was captured with `git status --porcelain=v1 -z --untracked-files=all`.
There were 258 NUL-delimited records. This is a raw record count, not a count of
reviewed files; renames can contain an extra path record. Earlier evaluations used
a different untracked-file aggregation, so their 148 status entries must not be
compared directly with this number.

The before/after status SHA-256 was identical:
`278a6e06b5b9fd6eb3e13566ebcd7c6698c9df57ca0432cfd99e2c3c4f20ec18`.
This shows the Git status listing did not change. It does not prove byte-for-byte
preservation: edits to an already modified file can leave that listing unchanged.
This limitation applies to the first scan, which did not retain byte inventories.

The repeat audit added a stronger check: the configured text-file path inventory
and every file's byte SHA-256 were identical immediately before and after the
scan. It covered 138 files, totaling 3,656,323 UTF-8 bytes and 83,186 text lines,
with no skipped files. The canonical inventory SHA-256 was
`b91b8b88e8d7062ba2e56be6a8c08cca086e88209705a040857d81cabb144d28`
both times. Configuration bytes and scanner hash also remained unchanged during
that repeat scan, and its Git status hashes matched the earlier value.

This proves matching observed before/after bytes within the configured text
scope. It is not an atomic filesystem snapshot, does not cover excluded runtime
directories, and cannot retroactively establish byte identity during the first
scan. Later AI opinions should bind to the retained report and input fingerprint.

## Five semantic review cases

All source paths and line numbers in this section refer to the observed target
checkout, not to RepoGC. Descriptions of tests mean their source was inspected;
the tests were not run during this evaluation.

### 1. Old status statements alongside later implementation

The selected card for `.harness/observations.md` contains status markers at lines
2991, 2992, and 3453 about incomplete MCP transports, plugin marketplace operations,
and interactive output-style selection.

Counterevidence exists in `src/plugins/runtime.js:654–768` for local marketplace
install, update backup, and recovery attempts; corresponding source tests begin at
`test/plugin-runtime.test.js:682`, `734`, `796`, and `866`. Output-style switching
and persistence appear in `src/cli/cli.js:2552–2585`, with command handling at
3513–3526 and a source test at `test/cli.test.js:2942`. The observations document
itself records later changes at 3522–3541 and 3585–3611.

A useful review would distinguish historical statements from current status and
propose clarifying their scope. It must not classify the entire log as useless or
claim these implementations passed a fresh runtime test. Local install support
also does not prove a remote marketplace service exists.

### 2. Omitted plan statements and configuration-dependent pending state

`.harness/plan.md:1054` and `1090` contain operational-state Findings that did not
reach the selected cards. Their IDs are
`a778a5cc3b066054f9441aff487f10eb6e1cd35a` and
`92c3f5c50b297b90ece183ad11e2d9adecd6c5d4`.

`src/mcp/runtime.js:106–109` determines connection behavior from configuration and
local URL status. Lines 2427–2465 include both intentional pending states and
actual connection/authentication handling. Source tests cover default remote URLs
remaining pending (`test/mcp-runtime.test.js:1707`), local HTTP connection (1739),
SSE response recovery (1840), WS connection (1934), and OAuth browser callbacks
(2669).

An AI should distinguish implemented transport support, a configured decision not
to connect, and unverified real external service behavior. An old annotation that
simply describes all remote transport as unimplemented cannot substitute for this
investigation. Consolidating similar concerns should retain the affected plan
statements, rather than showing only the observation-log representative.

### 3. Directory-tree examples are not required files at the document root

The selected `.harness/README.md` card contains four broken references from the
suggested directory tree at lines 129–141. Leaf names were interpreted relative to
`.harness/`, although the tree illustrates nested per-run/per-agent artifacts.
Lines 121–148 explain that context.

The AI should identify the example and resolver limitation before asking for new
files or removing documentation. The excluded `.harness/runs` directory was not
inspected, so this observation does not establish whether actual run artifacts
exist.

### 4. Navigation gaps do not establish that design evidence is obsolete

The default surface selects an orphan Finding for
`.harness/skills-runtime-evaluation-completion.md`, while omitting the unreachable
Finding for `.harness/skills-runtime-evolution-design.md`
(`9a907b66591a099f7d1683a52634b3dda12f72cb`).

The design document has three contextual inbound mentions: one from
`.harness/design-essence.md:3463` and two from the completion checklist at lines 5
and 11. These are not traversable Root paths. The checklist maps the design to
implementation stages at lines 5–18 and records acceptance criteria and follow-on
work at 48–65.

The useful question is whether these linked design and acceptance artifacts need
a formal entry or an explicit historical status. Lack of supported navigation is
not evidence that their design or audit purpose has disappeared. One navigation
discussion can retain both subjects and their different mechanical observations.

### 5. Dynamic Skill discovery as a counterexample to static-use verdicts

All 14 `skills/*/SKILL.md` files were declared Roots and reachable in this scan.
`src/systems/skills-runtime.js:762–797` discovers Skill documents dynamically, and
891–912 reads them into a catalog. `src/systems/context.js:571–600` obtains configured
roots from project settings and invokes that loader.

This demonstrates a concrete consumer mechanism and checks that declared host
entries were not mislabeled as navigation orphans. It does not establish actual
enablement or runtime access: `.brb/settings.json` and runtime traces were outside
the scan. A sound AI response retains that distinction rather than promoting a
Root declaration into proof that every Skill is currently used.

## Evaluation gaps and next evidence

- Inspecting selected cards alone misses the plan and design-document cases above.
  A semantic evaluation must inspect full reports and omitted subjects.
- The corpus is already familiar development material. A later held-out corpus
  needs separate selection and independent annotation before generalization claims.
- Source paths, quotes, and hashes can establish traceability, not the correctness
  of an AI interpretation. Record independent concerns and unresolved dimensions.
- Count reduction needs omission accounting and user corrections before it can
  support claims about reduced investigation or decision burden.
- No action, authorization, restoration, or user-outcome experiment took place.
  Those stages remain unassessed.

Related historical material: [review-first evaluation](review-first-best-runtime-box.md)
and [liveness evaluation](best-runtime-box-phase-0.7.md). Their dated observations
remain historical evidence, not a substitute for the fresh source review above.
