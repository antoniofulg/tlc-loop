"""Read task status out of git, and compose the trailers that write it.

Task completion has no status field anywhere in the plan: it lives in commit
trailers, and git is authoritative over `loop.json` (LOOP-01 AC 2). This module
is the only place that reads them.

Order is chronological. `git log --reverse` walks oldest to newest, so
"first seen" means "first committed", which is the order a reader expects.

A rebase or cherry-pick can leave the same `Task:` trailer on two commits. That
is not an error: the task is complete either way. The task counts once and the
duplication is handed back to the caller so the ambiguity can be recorded
rather than silently dropped.

Imported, never invoked directly.
"""

import os
import subprocess

TASK_TRAILER_FORMAT = "%(trailers:key=Task,valueonly)"


class GitError(RuntimeError):
    """A git invocation failed in a way the loop cannot interpret."""


def _run(args, root):
    return subprocess.run(
        ["git", "-C", os.path.abspath(root), *args],
        capture_output=True,
        text=True,
    )


def is_git_repo(root):
    """Whether `git rev-parse --git-dir` succeeds for this root."""
    return _run(["rev-parse", "--git-dir"], root).returncode == 0


def head_commit(root):
    """Full SHA of HEAD, or None when there is no commit to name yet.

    A verification covers the tree as it stood at one commit. Recording that
    SHA is what lets a later run tell a current PASS from one the code has
    since moved past.
    """
    proc = _run(["rev-parse", "HEAD"], root)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def completed_tasks(root):
    """Return `(ids, duplicates)` read from `Task:` commit trailers.

    `ids` holds each task once, in first-committed order. `duplicates` holds the
    ids that appeared on more than one commit, each listed once.
    """
    if not is_git_repo(root):
        raise GitError(f"not a git repository: {os.path.abspath(root)}")

    proc = _run(["log", "--reverse", f"--format={TASK_TRAILER_FORMAT}"], root)
    if proc.returncode != 0:
        if "does not have any commits" in proc.stderr:
            return [], []
        raise GitError(f"git log failed in {os.path.abspath(root)}: {proc.stderr.strip()}")

    ids, duplicates, seen = [], [], set()
    for line in proc.stdout.splitlines():
        # Commits with no Task: trailer emit an empty line. Skip them so they
        # never become an empty task id.
        value = line.strip()
        if not value:
            continue
        if value in seen:
            if value not in duplicates:
                duplicates.append(value)
            continue
        seen.add(value)
        ids.append(value)
    return ids, duplicates


def trailer_args(task_id, gate_level):
    """`git commit` arguments recording a task and its passing gate."""
    return ["--trailer", f"Task: {task_id}", "--trailer", f"Gate: {gate_level} PASS"]
