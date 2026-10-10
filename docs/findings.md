# Finding types and evidence

A Finding is a mechanically observable fact. A Candidate is an item for human
review. Neither is a verdict that an artifact is obsolete, unused, or safe to
delete.

## Categories

| Category | Mechanical meaning | Does not establish |
|---|---|---|
| `broken_reference` | A rendered Markdown link, image, reference definition or HTML `href`/`src` points to a repository path that does not exist, or differs from it only in letter case | Why the target is gone |
| `placeholder_text` | Rendered Markdown prose still contains known template instructions, such as an unreplaced `[INSERT CONTACT METHOD]` | What the replacement text should be |
| `orphan_candidate` | No non-self inbound reference was observed in the configured legacy orphan surface | That no human, dynamic, external, or process consumer exists |
| `unimplemented_marker` | A configured unfinished token was observed with lexical context | That the commitment is current or belongs to production code |
| `duplicate_candidate` | Normalized text similarity met the configured threshold | Equivalent authority, purpose, or safe consolidation |
| `unreachable_candidate` | No traversable strong path from configured Roots was observed | That the artifact is unused or safe to remove |

## Evidence strength

Reference edges retain strength and traversability. Source imports, configured
entry points, CI references, state-artifact references, Markdown links, and
declared contract references can be strong. Plain path mentions, examples, and
test references are contextual. Marker Findings use `review` or `contextual`
strength based on lexical role, not an AI judgment.

## Stable identity

Finding IDs derive from normalized source path and normalized evidence text, not
line number. Inserting unrelated lines should not create false trend churn. A
substantive evidence-text change may correctly produce a new ID.

## Liveness states

- `OBSERVED`: the configured mechanical surface produced evidence.
- `NOT_OBSERVED`: that surface did not produce evidence; absence is not proven.
- `DECLARED`: a human supplied an explicit source and reason; RepoGC did not
  independently observe the consumer.
- `UNKNOWN`: RepoGC did not inspect the surface.
- `NOT_INFERRED`: RepoGC deliberately refuses the semantic inference.
- `NOT_APPLICABLE`: the dimension cannot apply to this subject.

Use `repogc explain FINDING_ID` to view the Finding together with its liveness
profile, trend state, Git background, limitations, and review guidance.
