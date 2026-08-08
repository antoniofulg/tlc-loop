#!/usr/bin/env python3
"""checkpoint.py - create the atomic per-task commit that records status.

Task completion has no status field anywhere in the plan: it is written here,
as commit trailers, and read back by `detect_phase.py`. That makes this script
the point where a claim ("the gate passed") becomes durable evidence, so it is
deliberately suspicious of its caller.

Three refusals, in order, before anything is written:

1. **No asserted pass, no commit.** The caller must state `--gate-result PASS`
   exactly. A missing, failing, or differently-spelled assertion is a refusal
   (LOOP-02 AC 2). The gate decides whether a task is done; this script only
   records a decision that was already made.
2. **The message is validated first.** `check_commit.py` from the sibling skill
   runs *before* the index is touched, so a rejected message cannot leave a
   half-staged tree behind (LOOP-02 AC 3).
3. **A task that changed nothing still gets a commit.** `--allow-empty`, same
   `Task:` and `Gate:` trailers, and the line reports it as `empty`. LOOP-02
   AC 6 forbids fabricating a source diff, and an empty commit has none: it
   carries the trailers and nothing else. Recording the completion only in
   `loop.json` would put it in the one place git cannot rebuild, so deleting
   that file would re-dispatch a finished task.

Git hooks always run: this script never passes git a flag that would bypass
them, which is what keeps a project's own commit-msg or pre-commit guard in
force during an unattended run.

Usage:
    checkpoint.py <feature> --task TN --gate <quick|full|build> \\
                  --gate-result PASS --message "<conventional commit>" \\
                  [--path FILE ...] [--root DIR]

Exit codes: 0 committed. 1 the environment is unusable (no repository, sibling
skill missing, git failed). 2 the caller's request was refused (no asserted
pass, invalid message).
"""

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _gitio  # noqa: E402
import _paths  # noqa: E402

GATE_LEVELS = ("quick", "full", "build")

#: The exact assertion the caller must make. Compared literally: a typo must
#: refuse rather than commit.
PASS = "PASS"

TRAILER_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z-]*):[ \t]*(?P<value>.*)$")


def _git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)


def existing_trailer(message, key):
    """The value of a `Key: value` line already present in the message.

    Callers following the parent skill's commit convention put `Task:` and
    `Gate:` in the message body themselves. Appending them again would put two
    of each on one commit, and `_gitio.completed_tasks` reads a repeated
    `Task:` as the rebase ambiguity it is meant to catch. Every ordinary
    checkpoint would look ambiguous, so the trailer is added only when absent.
    """
    for line in message.splitlines():
        match = TRAILER_RE.match(line.strip())
        if match and match.group("key").lower() == key.lower():
            return match.group("value").strip()
    return None


def _traceability_paths(root, feature):
    """The feature's plan files, which ride along with the task's own files."""
    found = []
    for name in ("tasks.md", "spec.md"):
        rel = os.path.join(".specs", "features", feature, name)
        if os.path.isfile(os.path.join(root, rel)):
            found.append(rel)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="checkpoint.py",
        description="Commit one task atomically, with its Task: and Gate: trailers.",
    )
    parser.add_argument("feature")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    parser.add_argument("--task", required=True, metavar="TN")
    parser.add_argument("--gate", required=True, choices=GATE_LEVELS)
    parser.add_argument(
        "--gate-result",
        default=None,
        help=f"Must be exactly {PASS}; anything else refuses to commit",
    )
    parser.add_argument("--message", required=True, help="Conventional Commits message")
    parser.add_argument(
        "--path",
        action="append",
        metavar="FILE",
        help="Stage only this path (repeatable). Omitted: stage every change.",
    )
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    # 1. The caller must assert a passing gate.
    if args.gate_result != PASS:
        print(
            f"checkpoint: refusing to commit {args.task}: --gate-result must be "
            f"exactly {PASS}, got {args.gate_result!r}",
            file=sys.stderr,
        )
        return 2

    if not _gitio.is_git_repo(root):
        print(f"checkpoint: not a git repository: {root}", file=sys.stderr)
        return 1

    # A trailer the message already carries is kept, not repeated. One that
    # contradicts the flags is a refusal: a commit claiming two different
    # tasks or gate levels is exactly the ambiguity this script prevents.
    composed = _gitio.trailer_args(args.task, args.gate)
    trailers = []
    for item in composed[1::2]:
        key, _, value = item.partition(": ")
        present = existing_trailer(args.message, key)
        if present is None:
            trailers += ["--trailer", item]
        elif present != value:
            print(
                f"checkpoint: refusing to commit {args.task}: the message says "
                f"{key}: {present!r} but the flags say {value!r}",
                file=sys.stderr,
            )
            return 2

    # 2. Validate the message before the index is touched.
    try:
        validator = _paths.tlc_script("check_commit.py")
    except _paths.SiblingSkillError as exc:
        print(f"checkpoint: {exc}", file=sys.stderr)
        return 1
    checked = subprocess.run(
        [sys.executable, validator, "--message", args.message],
        capture_output=True,
        text=True,
    )
    if checked.returncode != 0:
        sys.stderr.write(checked.stdout)
        print(
            f"checkpoint: refusing to commit {args.task}: check_commit.py rejected "
            f"the message",
            file=sys.stderr,
        )
        return 2

    # 3. Stage the task's work.
    if args.path:
        paths = list(args.path) + _traceability_paths(root, args.feature)
        added = _git(root, "add", "--", *paths)
    else:
        added = _git(root, "add", "-A")
    if added.returncode != 0:
        print(f"checkpoint: git add failed: {added.stderr.strip()}", file=sys.stderr)
        return 1

    # 4. Nothing staged means the task legitimately produced no diff. It still
    #    gets a commit: the trailers are the only durable record of completion,
    #    and an empty commit carries them without fabricating a diff.
    empty = _git(root, "diff", "--cached", "--quiet").returncode == 0
    allow_empty = ["--allow-empty"] if empty else []

    # 5. Commit, carrying the trailers that record completion.
    committed = _git(root, "commit", "-q", "-m", args.message, *allow_empty, *trailers)
    if committed.returncode != 0:
        print(f"checkpoint: git commit failed: {committed.stderr.strip()}", file=sys.stderr)
        return 1

    sha = _git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    suffix = " empty" if empty else ""
    print(f"{sha} {args.task} gate={args.gate} {PASS}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
