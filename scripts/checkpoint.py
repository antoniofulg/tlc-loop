#!/usr/bin/env python3
"""checkpoint.py - the only writer of commits, in three named modes.

Task completion has no status field anywhere in the plan: it is written here,
as commit trailers, and read back by `detect_phase.py`. That makes this script
the point where a claim ("the gate passed") becomes durable evidence, so it is
deliberately suspicious of its caller.

Modes, and the phases each is allowed in:

* **default** - one task's atomic commit. Refused at `phase=E` and `phase=H`:
  a finished or halted run has nothing left to record, and a commit landing
  there is code no verifier has seen.
* **`--seal`** - the validation report, and nothing else, committed as a direct
  child of the commit it certifies. Allowed only at `phase=E`. This is the one
  exception to verification freshness in the whole skill; every rule it must
  satisfy is written out once, in `references/verification-freshness.md`.
* **`--reopen`** - a change that must land after a PASS anyway, such as a base
  branch that moved. Allowed only at `phase=E`, and it *invalidates* the
  verdict rather than carrying it: HEAD moves off the covered commit, the next
  detect opens a fresh epoch, and a new independent verification is owed.

Four refusals, in order, before anything is written:

1. **No asserted pass, no commit.** The caller must state `--gate-result PASS`
   exactly. A missing, failing, or differently-spelled assertion is a refusal
   (LOOP-02 AC 2). The gate decides whether a task is done; this script only
   records a decision that was already made.
2. **The phase is asked, not assumed.** `detect_phase.py` answers, and a
   situation it cannot read is a refusal rather than a guess.
3. **The gate matches the plan.** A task declaring `feature E2E` records
   `Gate: feature E2E PASS`. Coercing it to the nearest built-in level records
   that a different command passed, which is a false traceability entry.
4. **The message is validated first.** `check_commit.py` from the sibling skill
   runs *before* the index is touched, so a rejected message cannot leave a
   half-staged tree behind (LOOP-02 AC 3).

A task that changed nothing still gets a commit: `--allow-empty`, the same
`Task:` and `Gate:` trailers, and the line reports it as `empty`. The reason is
written out once, in `references/state-schema.md` under "The no-diff contract",
and nowhere else.

Git hooks always run: this script never passes git a flag that would bypass
them, which is what keeps a project's own commit-msg or pre-commit guard in
force during an unattended run.

Usage:
    checkpoint.py <feature> --task TN --gate <level> \\
                  --gate-result PASS --message "<conventional commit>" \\
                  [--path FILE ...] [--root DIR]
    checkpoint.py <feature> --seal [--root DIR]
    checkpoint.py <feature> --reopen --message "<conventional commit>" [--root DIR]

Exit codes: 0 committed. 1 the environment is unusable (no repository, sibling
skill missing, git failed). 2 the caller's request was refused (no asserted
pass, wrong phase, gate contradicts the plan, invalid message, invalid seal).
"""

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _gitio  # noqa: E402
import _paths  # noqa: E402
import _state_io  # noqa: E402
import _tasksmd  # noqa: E402

#: Gate levels a task may use without declaring one. A task that *does* declare
#: a gate is checked against its own declaration instead, so this list is a
#: fallback and not a vocabulary.
GATE_LEVELS = ("quick", "full", "build")

#: The exact assertion the caller must make. Compared literally: a typo must
#: refuse rather than commit.
PASS = "PASS"

TRAILER_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z-]*):[ \t]*(?P<value>.*)$")

HERE = os.path.dirname(os.path.realpath(__file__))


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


def _plan_path(root, feature):
    return os.path.join(root, ".specs", "features", feature, "tasks.md")


def _traceability_paths(root, feature):
    """The feature's plan files, which ride along with the task's own files."""
    found = []
    for name in ("tasks.md", "spec.md"):
        rel = os.path.join(".specs", "features", feature, name)
        if os.path.isfile(os.path.join(root, rel)):
            found.append(rel)
    return found


def detected_phase(root, feature):
    """The phase letter `detect_phase.py` reports, or None when it could not.

    Asking is what makes the commit rules enforceable rather than remembered.
    The detector is read-only and re-derives everything, so this costs one
    subprocess and cannot change the answer it is being asked about.
    """
    finished = subprocess.run(
        [sys.executable, os.path.join(HERE, "detect_phase.py"), feature, "--root", root],
        capture_output=True,
        text=True,
    )
    if finished.returncode != 0:
        return None
    line = finished.stdout.strip()
    if not line.startswith("phase="):
        return None
    return line[len("phase="):].split(" ", 1)[0]


def _same_gate(one, other):
    """Gate names compared the way a reader compares them."""
    return " ".join(one.lower().split()) == " ".join(other.lower().split())


def _declared_gate(root, feature, task):
    """The `Gate` the plan declares for a task, or None."""
    path = _plan_path(root, feature)
    if not os.path.isfile(path):
        return None
    wanted = task.upper()
    return next(
        (entry["gate"] for entry in _tasksmd.parse(path) if entry["id"] == wanted), None
    )


def _validated_message(message):
    """Run the sibling's validator. Returns an exit code, 0 when the message is fine."""
    try:
        validator = _paths.tlc_script("check_commit.py")
    except _paths.SiblingSkillError as exc:
        print(f"checkpoint: {exc}", file=sys.stderr)
        return 1
    checked = subprocess.run(
        [sys.executable, validator, "--message", message], capture_output=True, text=True
    )
    if checked.returncode != 0:
        sys.stderr.write(checked.stdout)
        return 2
    return 0


def _commit(root, message, trailers, allow_empty=False):
    """Commit, or report the git failure. Returns an exit code."""
    extra = ["--allow-empty"] if allow_empty else []
    committed = _git(root, "commit", "-q", "-m", message, *extra, *trailers)
    if committed.returncode != 0:
        print(f"checkpoint: git commit failed: {committed.stderr.strip()}", file=sys.stderr)
        return 1
    return 0


def seal(root, feature):
    """Commit the validation report as a seal over the commit it certifies.

    Every condition here exists so the exception stays narrow enough to trust.
    The phase gate above already required `phase=E`, which is what makes the
    report itself trustworthy: `detect_phase.py` reaches E only after the
    sibling's `validate_state.py` accepts the report as a filled PASS with
    `file:line` evidence, so a FAIL, an empty file, or a prose-only report can
    never get this far.
    """
    try:
        state = _state_io.load(feature, root)
    except _state_io.StateError as exc:
        print(f"checkpoint: refusing to seal: {exc}", file=sys.stderr)
        return 2

    verify = state.get("verify") or {}
    verified_at = verify.get("verified_at")
    head = _gitio.head_commit(root)
    if verify.get("last_verdict") != PASS or verified_at != head:
        print(
            f"checkpoint: refusing to seal: the seal must be a direct child of the "
            f"verified commit, and HEAD is {head}, not verified_at={verified_at} "
            f"(verdict {verify.get('last_verdict')!r})",
            file=sys.stderr,
        )
        return 2

    report = _gitio.report_path(feature)
    dirty = _gitio.dirty_paths(root, feature)
    if dirty != {report}:
        offenders = ", ".join(sorted(dirty - {report})) or "nothing to seal"
        print(
            f"checkpoint: refusing to seal: the seal's diff must be exactly "
            f"{report} and the tree carries {offenders}. Plan, design and status "
            f"updates belong before the final verification, not in this exception",
            file=sys.stderr,
        )
        return 2

    message = f"docs(verify): seal the validation report for {verified_at[:7]}"
    failed = _validated_message(message)
    if failed:
        print(f"checkpoint: check_commit.py rejected the seal message", file=sys.stderr)
        return failed

    added = _git(root, "add", "--", report)
    if added.returncode != 0:
        print(f"checkpoint: git add failed: {added.stderr.strip()}", file=sys.stderr)
        return 1

    failed = _commit(
        root,
        message,
        [
            "--trailer", f"{_gitio.SEAL_SUBJECT_TRAILER}: {verified_at}",
            "--trailer", f"{_gitio.SEAL_VERDICT_TRAILER}: {PASS}",
        ],
    )
    if failed:
        return failed

    sha = _git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    print(f"{sha} seal of {verified_at[:7]} {PASS}")
    return 0


def reopen(root, feature, message):
    """Commit a change that has to land after a PASS, and void the PASS.

    A base branch moving under a finished feature is the case this exists for.
    It cannot ride the seal's exception - the seal certifies a tree, and this
    changes one - so it does the opposite: the commit moves HEAD off the covered
    commit, which is exactly what makes the next detect ask for a fresh
    independent verification on a fresh epoch budget.

    No state is written. Git moving is the invalidation.
    """
    try:
        state = _state_io.load(feature, root)
    except _state_io.StateError as exc:
        print(f"checkpoint: refusing to reopen: {exc}", file=sys.stderr)
        return 2
    verified_at = ((state.get("verify") or {}).get("verified_at")) or "none"

    failed = _validated_message(message)
    if failed:
        print(f"checkpoint: check_commit.py rejected the message", file=sys.stderr)
        return failed

    added = _git(root, "add", "-A")
    if added.returncode != 0:
        print(f"checkpoint: git add failed: {added.stderr.strip()}", file=sys.stderr)
        return 1

    failed = _commit(root, message, ["--trailer", f"{_gitio.REOPEN_TRAILER}: {verified_at}"])
    if failed:
        return failed

    sha = _git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    print(f"{sha} reopened verification of {verified_at[:7]}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="checkpoint.py",
        description="Commit one task atomically, seal a verification, or reopen one.",
    )
    parser.add_argument("feature")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    parser.add_argument("--task", metavar="TN")
    parser.add_argument("--gate", help="The gate level the task declares")
    parser.add_argument(
        "--gate-result",
        default=None,
        help=f"Must be exactly {PASS}; anything else refuses to commit",
    )
    parser.add_argument("--message", help="Conventional Commits message")
    parser.add_argument(
        "--path",
        action="append",
        metavar="FILE",
        help="Stage only this path (repeatable). Omitted: stage every change.",
    )
    parser.add_argument(
        "--seal",
        action="store_true",
        help="Commit the validation report as a seal over the verified commit",
    )
    parser.add_argument(
        "--reopen",
        action="store_true",
        help="Commit a post-PASS change, invalidating the verdict it lands on",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = os.path.abspath(args.root)

    if args.seal and args.reopen:
        print("checkpoint: --seal and --reopen are different commits", file=sys.stderr)
        return 2
    mode = "seal" if args.seal else "reopen" if args.reopen else "task"

    missing = {
        "seal": [],
        "reopen": ["message"],
        "task": ["task", "gate", "message"],
    }[mode]
    absent = [f"--{name}" for name in missing if getattr(args, name) is None]
    if absent:
        print(f"checkpoint: {mode} needs {', '.join(absent)}", file=sys.stderr)
        return 2

    # 1. The caller must assert a passing gate. Seal and reopen carry no gate:
    #    one records a verdict that already passed, the other records that a
    #    verdict no longer applies.
    if mode == "task" and args.gate_result != PASS:
        print(
            f"checkpoint: refusing to commit {args.task}: --gate-result must be "
            f"exactly {PASS}, got {args.gate_result!r}",
            file=sys.stderr,
        )
        return 2

    if not _gitio.is_git_repo(root):
        print(f"checkpoint: not a git repository: {root}", file=sys.stderr)
        return 1

    # 2. The phase decides which commits are allowed at all. A run that is done
    #    or halted takes no ordinary commits: that is how the incident's two
    #    post-verification checkpoints would have been stopped.
    phase = detected_phase(root, args.feature)
    if phase is None:
        print(
            "checkpoint: refusing to commit: detect_phase.py could not read the "
            "situation, so no commit rule can be applied",
            file=sys.stderr,
        )
        return 2
    if mode == "task" and phase in ("E", "H"):
        print(
            f"checkpoint: refusing to commit {args.task}: the detector reports "
            f"phase={phase}. A finished or halted run takes no further ordinary "
            f"commits; use --reopen for a change that must land anyway",
            file=sys.stderr,
        )
        return 2
    if mode in ("seal", "reopen") and phase != "E":
        print(
            f"checkpoint: refusing to {mode}: the detector reports phase={phase}, "
            f"not E, so there is no current verdict to {'certify' if mode == 'seal' else 'invalidate'}",
            file=sys.stderr,
        )
        return 2

    if mode == "seal":
        return seal(root, args.feature)
    if mode == "reopen":
        return reopen(root, args.feature, args.message)

    # 3. The recorded gate is the gate the plan asked for.
    declared = _declared_gate(root, args.feature, args.task)
    if declared:
        if not _same_gate(args.gate, declared):
            print(
                f"checkpoint: refusing to commit {args.task}: the plan declares "
                f"gate {declared!r} and the flags say {args.gate!r}",
                file=sys.stderr,
            )
            return 2
    elif args.gate not in GATE_LEVELS:
        print(
            f"checkpoint: refusing to commit {args.task}: {args.gate!r} is not a "
            f"known gate level ({', '.join(GATE_LEVELS)}) and the plan declares "
            f"none for this task",
            file=sys.stderr,
        )
        return 2

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

    # 4. Validate the message before the index is touched.
    failed = _validated_message(args.message)
    if failed:
        print(
            f"checkpoint: refusing to commit {args.task}: check_commit.py rejected "
            f"the message",
            file=sys.stderr,
        )
        return failed

    # 5. Mark the plan in the same commit as the gate that earned the mark.
    plan = _plan_path(root, args.feature)
    if os.path.isfile(plan):
        _tasksmd.mark_done(plan, args.task)

    # 6. Stage the task's work.
    if args.path:
        paths = list(args.path) + _traceability_paths(root, args.feature)
        added = _git(root, "add", "--", *paths)
    else:
        added = _git(root, "add", "-A")
    if added.returncode != 0:
        print(f"checkpoint: git add failed: {added.stderr.strip()}", file=sys.stderr)
        return 1

    # 7. Nothing staged means the task legitimately changed nothing. It still
    #    gets a commit; see the no-diff contract in `references/state-schema.md`.
    empty = _git(root, "diff", "--cached", "--quiet").returncode == 0

    failed = _commit(root, args.message, trailers, allow_empty=empty)
    if failed:
        return failed

    sha = _git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    suffix = " empty" if empty else ""
    print(f"{sha} {args.task} gate={args.gate} {PASS}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
