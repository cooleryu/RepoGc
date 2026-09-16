# Local package evaluation: Phase 1

- Date: 2026-09-02
- Source commit: `140c87b422be4a1f4285060fbaa23e8b9d6b9145`
- Package version: `0.0.0` (unreleased)
- Build frontend: `uv 0.11.1`
- Install interpreter: Python 3.12
- Publication: none

## Build

The source checkout was clean before the formal build. Build isolation produced:

| Artifact | Size | SHA-256 |
|---|---:|---|
| `repogc-0.0.0.tar.gz` | 69,234 bytes | `b2d928e3be81968dd2cf233660ef690c2334977a56dc51a514b25072842ffe85` |
| `repogc-0.0.0-py3-none-any.whl` | 33,939 bytes | `99554613802fea4c1be85f97e31f894729f622248d3a36b5931d972c17afbbbc` |

The source distribution contained 61 entries. Explicit checks confirmed that it
included:

- `repogc.toml`;
- the GC manual;
- architecture and public documentation;
- Phase 0.7's decision record;
- the Best Runtime Box corpus configuration.

The first local build needed to download the declared `setuptools>=69` build
dependency into a temporary cache. The formal clean-commit build then succeeded
offline from that cache. No package was uploaded.

## Isolated install

The wheel was installed with `--no-deps` into a newly created Python 3.12 virtual
environment. Import inspection resolved `repogc` from that environment's
`site-packages`, not from the source checkout, and reported Schema `0.4`.

The installed command then completed:

- `repogc --help`;
- `repogc doctor` with all C1-C6 and G1-G5 sentinels passing;
- `repogc scan ... --no-write` against the RepoGC checkout;
- a `RELIABLE` result with no report or baseline writes.

## Build-artifact regression

The first build revealed that standard `*.egg-info` metadata could enter a
subsequent dogfood scan and create four synthetic unreachable candidates. Phase 1
therefore added a visible default exclusion and a regression test. A scan with
the generated metadata still present then returned zero unreachable candidates.
The generated source-tree metadata was removed after validation.

## Limits

- The GitHub Actions workflow is syntactically validated locally but has not run
  on a public remote.
- Linux behavior is represented by the workflow definition, not by this macOS
  execution.
- Windows remains untested and is not included in the CI matrix.
- Version, final name, License, release signing, and package-index publication
  remain unapproved.
