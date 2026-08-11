#!/usr/bin/env python3
"""finish_loop.py - the only path to the done-signature.

The signature means one thing: an independent verifier passed the tree that is
checked out right now. Deciding that was prose in `SKILL.md` until a real run
printed it over a tree two commits past the only verdict on record - every gate
green, the detector correctly answering `phase=H`, and the conclusion reached
anyway. A rule a model applies is a rule a model can be talked out of.

So the decision moved here. Nothing else in this skill may print the line, and
this script re-derives every fact it rests on rather than being told any of them:

1. `detect_phase.py` says exactly `phase=E action=done`.
2. The working tree carries no change (bar the loop's own `loop.json`, which is
   machine state and belongs in `.gitignore`).
3. HEAD is the verified commit, or a valid seal over it.
4. Completion is recorded through `update_loop.py`, the single writer.
5. Steps 1 to 3 hold *again*, and HEAD has not moved since step 1.
6. The signature is printed, as the last line.

Step 5 is not paranoia about itself. Checking once and then acting is a race
with everything else on the machine, and the window it closes is the same shape
as the incident: something committed while the run believed it was finished.

`--preflight <base>` answers a different question - "is this safe to publish" -
with the same checks plus one: the base ref must already be an ancestor of HEAD.
It writes nothing and never prints the signature. Pushing and opening a PR stay
outside this skill and outside its authorization (`SKILL.md`, blast radius).

Usage:
    finish_loop.py <feature> [--root DIR]
    finish_loop.py <feature> [--root DIR] --preflight <base-ref>

Exit codes: 0 the run is finished (or the preflight passed), 1 the situation
could not be read, 2 the request was refused with the reason on stderr.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _gitio  # noqa: E402
import _state_io  # noqa: E402

HERE = os.path.dirname(os.path.realpath(__file__))

#: The literal the goal evaluators and `references/checklist.md` match on. It
#: exists in this file and nowhere else in `scripts/`, which is what makes
#: matching it equivalent to trusting this script's decision.
SIGNATURE = "__TLC_LOOP__ feature={feature} verify=PASS"

DONE_LINE = "phase=E action=done"


def _git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)


def blocking_reason(feature, root):
    """Why this run may not be signed for, or None when every condition holds.

    Read-only, and cheap enough to run twice - which is the point.
    """
    detected = subprocess.run(
        [sys.executable, os.path.join(HERE, "detect_phase.py"), feature, "--root", root],
        capture_output=True,
        text=True,
    )
    if detected.returncode != 0:
        return f"detect_phase.py could not read the situation: {detected.stderr.strip()}"
    line = detected.stdout.strip()
    if not line.startswith(DONE_LINE):
        return f"the detector says {line!r}, not {DONE_LINE!r}"

    dirty = _gitio.dirty_paths(root, feature)
    if dirty:
        return (
            "the working tree carries changes no verifier has seen: "
            + ", ".join(sorted(dirty))
            + ". Commit the validation report with `checkpoint.py --seal`; "
            "anything else reopens verification"
        )

    try:
        state = _state_io.load(feature, root)
    except _state_io.StateError as exc:
        return str(exc)
    if not _gitio.verification_covers_head(state, root, feature):
        return (
            "HEAD is neither the verified commit nor a valid seal over it, so "
            "the recorded verdict does not describe this tree"
        )
    return None


def preflight(feature, root, base):
    """Answer whether HEAD is safe to publish against `base`. Writes nothing."""
    blocked = blocking_reason(feature, root)
    if blocked:
        print(f"finish_loop: not publishable: {blocked}", file=sys.stderr)
        return 2

    resolved = _git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if resolved.returncode != 0:
        print(f"finish_loop: no such base ref: {base}", file=sys.stderr)
        return 1

    ancestor = _git(root, "merge-base", "--is-ancestor", base, "HEAD")
    if ancestor.returncode != 0:
        print(
            f"finish_loop: not publishable: {base} has moved ahead of HEAD, so a "
            f"push or PR would carry a merge nobody verified. Integrate {base} "
            f"with `checkpoint.py --reopen`, re-run the gates, take a fresh "
            f"independent verification, seal it, then finish",
            file=sys.stderr,
        )
        return 2

    print(f"preflight ok feature={feature} base={base} head={_gitio.head_commit(root)}")
    return 0


def finish(feature, root):
    """Record completion and print the signature, or refuse and say why."""
    before = _gitio.head_commit(root)
    blocked = blocking_reason(feature, root)
    if blocked:
        print(f"finish_loop: refusing to sign: {blocked}", file=sys.stderr)
        return 2

    recorded = subprocess.run(
        [
            sys.executable, os.path.join(HERE, "update_loop.py"), feature,
            "--root", root, "--status", "complete", "--iteration-done",
            "--phase", "E", "--action", "done",
        ],
        capture_output=True,
        text=True,
    )
    # HEAD is compared before the writer's exit code is interpreted. A tree that
    # moved is the cause; the writer refusing is only how it showed up, and the
    # cause is the more useful thing to print.
    after = _gitio.head_commit(root)
    if after != before:
        print(
            f"finish_loop: refusing to sign: HEAD moved from {before} to {after} "
            f"while completion was being recorded",
            file=sys.stderr,
        )
        return 2
    if recorded.returncode != 0:
        sys.stderr.write(recorded.stderr)
        print("finish_loop: refusing to sign: completion could not be recorded",
              file=sys.stderr)
        return 2
    sys.stdout.write(recorded.stdout)

    blocked = blocking_reason(feature, root)
    if blocked:
        print(f"finish_loop: refusing to sign: {blocked}", file=sys.stderr)
        return 2

    print(SIGNATURE.format(feature=feature))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="finish_loop.py",
        description="Record completion and print the done-signature, or refuse.",
    )
    parser.add_argument("feature")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    parser.add_argument(
        "--preflight",
        metavar="BASE",
        help="Read-only: report whether HEAD is safe to publish against this ref",
    )
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    if not _gitio.is_git_repo(root):
        print(f"finish_loop: not a git repository: {root}", file=sys.stderr)
        return 1
    if args.preflight:
        return preflight(args.feature, root, args.preflight)
    return finish(args.feature, root)


if __name__ == "__main__":
    raise SystemExit(main())
