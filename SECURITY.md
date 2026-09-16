# Security policy

RepoGC is an experimental preview without a supported stable version. Do not use the current
repository as an authorization source for automated deletion or repository
mutation.

## Security properties

The current scanner is designed to avoid executing target-repository code,
following file symlinks, making network requests, writing outside configured
repository-relative report paths, or updating a baseline from a non-reliable
report. These properties are covered by tests but are not a formal sandbox or a
guarantee that every hostile filesystem case has been handled.

Git metadata reads now disable fsmonitor, hooks, signature display, optional
index writes, automatic maintenance and transports, and remove inherited Git
redirection. If content filters are configured or inspection fails, working-tree
status is skipped and remains unknown. These checks assume trusted host Git and
stable inputs; they are not an OS sandbox or protection against concurrent hostile
filesystem mutation. Keep `[scan] use_git = false` for untrusted checkouts when
Git background is unnecessary. Synthetic evaluation always disables Git.

Explicit evidence bundles contain configured source text and can contain secrets.
They are local, not redacted public artifacts. Verification does not authenticate
their author, establish semantic truth or authorize execution.

## Reporting a vulnerability

Use GitHub private vulnerability reporting through the repository's Security
tab when enabled. If unavailable, request a private contact without disclosing
the vulnerability in a public issue. Do not publish target-repository content, credentials, personal
paths, or an exploit containing private data.

Include the affected version or commit, platform, minimal reproduction, expected
boundary, observed behavior, and whether the issue can cause code execution,
path escape, data disclosure, report tampering, or unsafe baseline mutation.

This project does not yet promise a response-time service level.
