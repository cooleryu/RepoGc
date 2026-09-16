# 0009: RepoGC name and Apache-2.0 license

Status: accepted. [human-approved 2026-09-07]

The owner selected RepoGC as the public project name and Apache License 2.0
as the project license. Python package and CLI names remain `repogc`.

Public positioning: Garbage collection for AI-heavy repositories.
Report first. Humans decide.

GC describes identifying and reviewing potentially obsolete artifacts. Static
absence does not prove an artifact is unused. The current implementation reports
candidates and context; people make retention and deletion decisions.

The root LICENSE contains the complete Apache-2.0 text. Package metadata refers
to it, and source and wheel distributions must include it. Original project
code and documentation use this license; external repositories retain their own
terms. No third-party attribution is invented by this decision.

This supersedes earlier records saying the name or license was undecided.
Historical evaluation records remain dated evidence. The development version
remains 0.0.0 until a release is approved. This decision does not itself publish
a remote repository or upload a package.
