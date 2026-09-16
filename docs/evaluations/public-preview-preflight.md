# Public preview preflight

Date: 2026-09-16. This is release preparation, not a product-value evaluation.

## Onboarding and reproducibility

- README now describes review of current repository state, without assuming a
  newly introduced module or completed future work.
- The synthetic first-review example contains a broken setup link and a staged
  design document whose absent incoming link does not justify removal.
- 99 unit tests passed locally, including the unchanged-demo check.
- All 15 doctor sentinels passed. Self-scan was RELIABLE; that is not a claim
  that all findings are actionable or that the repository has no issues.
- All 11 development evaluation cases passed. The fresh evaluation records
  AI review and human outcome as not run.
- Wheel and source archive built in a temporary isolated environment. The wheel
  installed offline; all 99 tests passed from the extracted source archive.
- Installed CLI produced two cards from five synthetic signals. Full evidence
  retained all five findings, with three not shown, and verified successfully.
- The Linux/macOS CI definition now includes the walkthrough and development
  evaluation. Both referenced official Action version tags were checked to exist.

## Publication audit

- Inspected all 198 reachable historical blobs across 23 local commits, plus
  tracked and nonignored working files, using targeted patterns for common
  credential formats, secret assignments, machine paths and email addresses.
- No credential-pattern matches were found. This limited check is not a full
  secret scanner, security audit or guarantee that sensitive data is absent.
- Personal machine paths were found in historical evaluation prose and removed
  from current public documents. Old commits still contain them.
- Historical commit metadata contains a personal email. Working-file email
  matches are synthetic test addresses under the reserved example.invalid domain.
- Source inventory review found original code, synthetic fixtures, aggregate
  evaluation descriptions and RepoGC self-scan artifacts. Private corpus source
  bundles and local evaluation archives are excluded. No corpus source is being
  relicensed under RepoGC's Apache-2.0 license.
- Environment-file and desktop-metadata exclusions were added. Ignoring a file
  does not remove it from history.

## Detailed publication recheck

The owner requested a detailed recheck before the first push. A separate clean
publication copy retains the reviewed current files, not the old Git history.
The original checkout, all 23 commits and local evidence archives remain local
and unchanged by the copy operation.

- The initial publication inventory contained 110 regular UTF-8 files (643,049
  bytes). Its path-list SHA-256 was
  `f2448a6b125bd2085401d1f6b8ebbc365c615d9d6ea963c69c1f9d0f41ee2893`.
  Subsequent edits to this audit record change the byte total, not that inventory.
- Every copied file initially matched its original working-tree bytes; no
  extra files, missing files, symlinks, environment files or binary payloads
  were present. All included JSON files parsed.
- Expanded checks found no personal home paths, personal account identifiers,
  phone/identity-number patterns, IPv4 addresses, credential-bearing URLs or
  JWTs. Three email occurrences are deliberate reserved-domain test values.
- Gitleaks 8.30.1 scanned the publication files and all 23 original commits
  with default rules and redacted reporting: no leaks found. The official
  macOS ARM64 archive matched the publisher's SHA-256:
  `b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5`.
- The new publication history uses the account's GitHub noreply identity.
  Old commits and their personal author email are not pushed. Public owner and
  repository links are intentional, not anonymized.

These are scoped, reproducible checks, not a guarantee that every possible
secret or privacy concern is detectable. RepoGC itself is not a secret scanner.
Remote CI and a public clone are checked after pushing; local tests alone do
not establish remote success.

See [the public-preview decision](../decisions/0014-public-preview.md).
