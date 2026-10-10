from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1",
    })
    return subprocess.run(
        ["git", "--no-pager", "--no-optional-locks",
         "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull,
         "-c", "core.untrackedCache=false", "-c", "gc.auto=0",
         "-c", "maintenance.auto=false", "-c", "protocol.allow=never",
         "-c", "log.showSignature=false",
         "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def repository_info(
    root: Path, enabled: bool
) -> tuple[dict[str, str | bool | None], str | None]:
    if not enabled:
        return {"commit": None, "branch": None, "dirty": None}, None
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return (
            {"commit": None, "branch": None, "dirty": None},
            "Git metadata unavailable: not a Git work tree.",
        )

    commit_result = _git(root, "rev-parse", "HEAD")
    branch_result = _git(root, "branch", "--show-current")
    # Status may run clean/process filters while comparing working-tree content.
    # Do not invoke it when such helpers are configured or cannot be inspected.
    filters = _git(root, "config", "--includes", "--name-only", "--get-regexp",
                   r"^filter\..*\.(clean|process)$")
    status_result = (None if filters.returncode != 1 else
                     _git(root, "status", "--porcelain=v1", "--untracked-files=all"))
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "UNBORN"
    branch = branch_result.stdout.strip() or None
    dirty = (bool(status_result.stdout.strip())
             if status_result is not None and status_result.returncode == 0 else None)
    repository = {"commit": commit, "branch": branch, "dirty": dirty}
    if commit_result.returncode != 0:
        return (
            repository,
            "Git HEAD unavailable: repository has no commit yet.",
        )
    if status_result is None:
        return repository, "Git working-tree status skipped: content filters configured or filter inspection unavailable."
    if status_result.returncode != 0:
        return repository, "Git working-tree status unavailable."
    return repository, None


def last_touch(root: Path, relative_path: str, enabled: bool) -> dict[str, str] | None:
    if not enabled:
        return None
    result = _git(
        root,
        "log",
        "-1",
        "--format=%cI%x00%H",
        "--",
        relative_path,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    parts = result.stdout.rstrip("\n").split("\x00")
    if len(parts) != 2:
        return None
    return {"date": parts[0], "commit": parts[1]}


def repository_files(root: Path, enabled: bool) -> tuple[set[str], set[str]] | None:
    """Return (files that belong to the repository, files Git tracks).

    Repository files are tracked or untracked-but-not-ignored. Tracked files
    include entries that a sparse or partial checkout left off disk. Returns
    None when Git is disabled or unavailable. ``ls-files`` reads the index and
    ignore rules only; it does not run content filters.
    """
    if not enabled:
        return None
    tracked = _git(root, "ls-files", "-z", "--cached")
    untracked = _git(root, "ls-files", "-z", "--others", "--exclude-standard")
    if tracked.returncode != 0 or untracked.returncode != 0:
        return None
    tracked_files = {item for item in tracked.stdout.split("\0") if item}
    untracked_files = {item for item in untracked.stdout.split("\0") if item}
    return tracked_files | untracked_files, tracked_files
