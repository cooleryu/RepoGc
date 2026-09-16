# Configuration reference

RepoGC uses `repogc.toml` from the target repository by default. Pass an explicit
path with `--config`; relative paths are resolved against the target repository.
If no file exists, built-in defaults are used.

## Minimal configuration

```toml
[scan]
use_git = true

[reports]
markdown = "docs/gc_reports/latest.md"
json = "docs/gc_reports/latest.json"
baseline = "reference/gc_reports/baseline.json"
```

## `[scan]`

| Key | Meaning |
|---|---|
| `include_suffixes` | Text suffixes eligible for scanning |
| `orphan_suffixes` | Suffixes eligible for unreferenced-document candidates |
| `duplicate_suffixes` | Suffixes eligible for similarity comparison |
| `exclude_dirs` | Exact directory names or repository-relative directory paths |
| `exclude_globs` | File globs excluded from scanning |
| `root_files` | Legacy root-file list used by orphan handling |
| `max_file_bytes` | Files above this size are skipped and make coverage partial |
| `duplicate_threshold` | Normalized similarity threshold from `0.0` to `1.0` |
| `duplicate_min_chars` | Minimum normalized text length for duplicate comparison |
| `use_git` | Enable bounded read-only Git metadata collection |

Standard Python `*.egg-info` build metadata is excluded by the built-in defaults.
Generated, vendored, report, and cache directories should be declared explicitly
for each repository rather than hidden in detector code.

## `[markers]`

`tokens` lists unfinished-work tokens. ASCII tokens are exact-case and token
bounded. Chinese tokens are matched literally. Marker context classification
distinguishes source comments, strings, tests, generated files, Markdown code,
contract prose, tasks, and declared harness state.

```toml
[markers]
tokens = ["TODO", "FIXME", "NOT_IMPLEMENTED", "未实现", "待实现"]
```

An empty array disables marker Findings.

## `[graph]`

| Key | Meaning |
|---|---|
| `root_globs` | Explicit, human-reviewable GC Roots; defaults include Codex-discovered `.agents/skills/**/SKILL.md` contracts |
| `instruction_globs` | Agent or skill instruction files |
| `contract_globs` | Files where contract cues can create strong edges |
| `test_globs` | Test and fixture roles; references remain contextual |
| `generated_globs` | Generated artifact roles |
| `ci_globs` | CI files whose references may be strong and sensitive |
| `config_globs` | Structured configuration files |
| `config_reference_keys` | JSON keys that identify package/config references |
| `state_reference_keys` | JSON keys that identify harness-state artifacts |

Roots are declarations, not AI guesses. A file that does not match a Root may
still have dynamic, external, runtime, human, legal, or business consumers that
RepoGC cannot observe.

## `[[liveness.declarations]]`

Use an exact-path declaration when a reviewer knows about evidence that static
analysis cannot observe:

```toml
[[liveness.declarations]]
path = "records/process_log.md"
kind = "dynamic_consumer"
source = "case registry"
reason = "Loaded from a computed case directory at runtime."
```

Supported kinds are `retention`, `dynamic_consumer`,
`external_system_consumer`, and `runtime_access`. All four fields are required.
Paths must be repository-relative and cannot contain `..`.

Declarations are labeled `DECLARED`, not mechanically observed. They do not
suppress Findings, create graph edges, establish reachability, or prove their
own freshness. Unmatched declarations remain visible in the report so stale
configuration can be reviewed.

## `[reports]`

`markdown`, `json`, and `baseline` must be repository-relative paths. RepoGC
rejects absolute paths and paths that escape the target repository. A normal
scan writes reports but never updates the baseline. Use `repogc baseline
--update` only after reviewing a `RELIABLE` report.

## Validation behavior

Configuration arrays must contain only strings. File size must be positive,
duplicate thresholds must stay within `0.0..1.0`, and output paths must remain
inside the target repository. The complete effective configuration is hashed so
changes are disclosed as a trend-basis change.
