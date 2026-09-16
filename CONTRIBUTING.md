# Contributing to RepoGC

RepoGC welcomes evidence-backed improvements to deterministic repository entropy
observation. RepoGC is licensed under the [Apache License, Version 2.0](LICENSE).
Contributions intentionally submitted for inclusion are under the same license
unless explicitly stated otherwise, as described in Section 5. Preserve
applicable third-party notices when contributing external material.

Read [AGENTS.md](AGENTS.md), the [north star](docs/NORTH_STAR.md), and the
[constitution](docs/CONSTITUTION.md) before changes. The
[engineering and evaluation plan](docs/ENGINEERING_AND_EVALUATION.md) defines
the implementation stages, acceptance criteria, and separate engineering, AI,
and human-value evidence.

## Development setup

Python 3.11 or newer is required. The runtime has no third-party dependencies.

```sh
python -m pip install .
python -m unittest discover -s tests -p 'test*.py' -v
repogc doctor . --config repogc.toml
repogc scan . --config repogc.toml --no-write
```

## Change expectations

- Start from a minimal reproducible case.
- Keep scanning deterministic, local-first, and report-only.
- Add a fixture that distinguishes behavior before and after the change.
- Run historical C1-C6 regressions and all current sentinels.
- Preserve mechanical and optional AI boundaries.
- Update documentation when configuration, CLI, report Schema, or known limits
  change.
- Compare scan results and disclose scanner, configuration, or Schema basis
  changes.
- Never describe a Candidate as safe to remove.

New heuristic detectors normally require at least three real cases with a shared
mechanical rule and documented false-positive boundaries. A clever-sounding
detector without evidence does not belong in the core.

## Development-case evaluation

From a source checkout, choose a new output directory for each run:

```sh
PYTHONPATH=src python3.12 -m evals.run --output /tmp/repogc-eval-first-run
```

Use Python 3.11 or newer. The development cases live in
[evals/cases.json](evals/cases.json); they are known regression cases, not a
held-out benchmark. Preserve failed cases and explain any change to expectations.
Keep run outputs and private source snapshots out of the public source tree.

The run saves engineering results and material for a separate AI review. It does
not call a model automatically. Record AI and human evaluations as `not_run`
until they actually happen; a structurally valid AI review does not prove its
conclusions correct. Apply the plan's rubric, cite concrete evidence, and record
whether a reviewer shares the implementing agent's model or session. A real
human-value study requires observed human participation.

After writing a separate AI review record, validate its evidence binding with:

```sh
PYTHONPATH=src python3.12 -m evals.run \
  --check-ai-review /tmp/repogc-ai-review.json \
  --run-dir /tmp/repogc-eval-first-run
```

The checker reports record validity, coverage and concerns separately; it leaves
the original run summary unchanged. The review format and five required rubric
dimensions are documented in the engineering and evaluation plan.

## Core semantic changes

Finding identity, baseline logic, reference parsing, self-checks, reliability,
report Schema, and trend meaning require a decision record, migration plan,
rollback method, and dedicated regression test. Automatic deletion, AI verdicts,
or weakening human review require explicit owner approval and are outside normal
contribution scope.

## Pull request evidence

A future pull request should state the problem, real case, exact files changed,
behavioral difference, validation commands, scan-count impact, remaining limits,
and rollback path. Commit messages are context, not proof that a mechanism is
dead or unused.
