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

#: The trailers a verification seal carries, and the one a reopen carries. The
#: seal is the only commit allowed to follow a PASS without unverifying the
#: tree; `references/verification-freshness.md` is the single description of
#: why, and of everything the seal is not allowed to contain.
SEAL_SUBJECT_TRAILER = "Verification-Of"
SEAL_VERDICT_TRAILER = "Verification-Result"
REOPEN_TRAILER = "Reopens-Verification"


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


# --- verification freshness -------------------------------------------------
#
# One predicate, four callers: the detector, the state writer, the checkpoint
# and the finalizer all have to agree on whether the recorded verdict describes
# the tree as it stands. Four implementations of that would be four chances to
# disagree, and the run that produced this module disagreed with itself once
# already.


def report_path(feature):
    """The canonical validation report, spelled the way git reports it."""
    return f".specs/features/{feature}/validation.md"


def trailer(root, rev, key):
    """The value of one trailer on one commit, or `""`."""
    proc = _run(["log", "-1", f"--format=%(trailers:key={key},valueonly)", rev], root)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def parents(root, rev):
    """Full SHAs of a commit's parents, in order."""
    proc = _run(["rev-list", "--parents", "-n", "1", rev], root)
    return proc.stdout.split()[1:] if proc.returncode == 0 else []


def changed_files(root, rev):
    """Paths a non-merge commit changed."""
    proc = _run(["show", "--name-only", "--format=", rev], root)
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def dirty_paths(root, feature):
    """Working-tree changes, staged or not, excluding the loop's own state.

    `loop.json` is one run's private bookkeeping and belongs in the project's
    `.gitignore` (`references/state-schema.md`). A project that never added the
    rule still has a clean tree as far as the *verified code* is concerned, so
    the file is excluded here rather than being allowed to block a seal or a
    finish over bookkeeping no verifier was ever asked to look at.
    """
    # `--untracked-files=all` because the default collapses a wholly untracked
    # directory to `.specs/`, which no exclusion below could ever match and
    # which tells a caller nothing about what is actually in the way.
    proc = _run(["status", "--porcelain", "--untracked-files=all"], root)
    machine_state = f".specs/features/{feature}/loop.json"
    found = set()
    for line in proc.stdout.splitlines():
        entry = line[3:]
        if " -> " in entry:  # a rename reports both sides
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry and entry != machine_state:
            found.add(entry)
    return found


def is_seal(root, feature, rev, verified_at):
    """Whether `rev` is a valid verification seal over `verified_at`.

    All four facts are re-derived from git rather than read from the trailers
    alone: a trailer is a claim, and the whole point of the seal is that it is
    the one post-verification commit narrow enough to check.
    """
    return bool(verified_at) and (
        parents(root, rev) == [verified_at]
        and trailer(root, rev, SEAL_SUBJECT_TRAILER) == verified_at
        and trailer(root, rev, SEAL_VERDICT_TRAILER) == "PASS"
        and changed_files(root, rev) == [report_path(feature)]
    )


def verification_covers_head(state, root, feature):
    """Whether the recorded verdict describes the tree as it stands now.

    Two ways to be covered, and no third: HEAD *is* the verified commit, or
    HEAD is a seal that certifies it. Anything else - a task, a fix, a merge, a
    documentation edit - is code no verifier has seen, however small.

    An absent `verified_at` counts as uncovered. That is the state a rebuilt
    `loop.json` is in, and it costs one verify round rather than ever declaring
    an unverified tree done.
    """
    verified_at = ((state.get("verify") or {}).get("verified_at")) or None
    head = head_commit(root)
    if verified_at is None or head is None:
        return False
    return head == verified_at or is_seal(root, feature, head, verified_at)
