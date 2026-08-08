#!/usr/bin/env python3
"""update_loop.py - the only mutator of `loop.json` after bootstrap.

`loop.json` has a single writer (LOOP-01 AC 6). Every counter the halt
conditions read is written here and nowhere else, so a run's stop conditions
have exactly one origin.

Two invariants are enforced rather than documented:

* **The objective is immutable** (D12). It is fixed at bootstrap and there is
  no route through this script to change it. A call that tries is rejected
  before the state file is even read, so a rejected call cannot half-apply its
  other flags.
* **The iteration log is append-only and capped.** Entries are appended and the
  file keeps only the last 50, which bounds the file without ever rewriting
  history.

`iterations_without_commit` is the no-progress detector (LOOP-06 AC 6). A
recorded commit resets it; an iteration that closes without one increments it.

Usage:
    update_loop.py <feature> [--root DIR] <one or more actions>

Exit codes: 0 the state was written, 1 the state could not be read or written,
2 the invocation was rejected (immutable field, unknown value, nothing to do).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _gitio
import _state_io  # noqa: E402

#: The iteration log keeps this many of the most recent entries.
LOG_LIMIT = 50

#: Halt reasons `detect_phase.py` can print, so one vocabulary covers both the
#: recorded halts and the derived ones. `state_corrupt` is derived - the state
#: could not be read, so in practice it cannot be written back either - but it
#: is listed here because the constant is the vocabulary, not the storage.
HALT_REASONS = (
    "no_progress",
    "gate_stuck",
    "executor",
    "limit",
    "blocker",
    "blast_radius",
    "state_corrupt",
    "verify_exhausted",
)

VERDICTS = ("PASS", "FAIL")

#: Flags that change state. An invocation carrying none of them is a no-op and
#: is rejected, so a mistyped call cannot look like it worked.
ACTION_FLAGS = (
    "iteration_done",
    "batch",
    "task_started",
    "task_done",
    "reconciled",
    "commit",
    "gate_attempt",
    "verify_round",
    "gaps",
    "report",
    "halt",
    "status",
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="update_loop.py",
        description="Record loop progress in loop.json. The only writer after bootstrap.",
    )
    parser.add_argument("feature")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    parser.add_argument(
        "--iteration-done",
        action="store_true",
        help="Close the iteration: bump the counter and append a log entry",
    )
    parser.add_argument("--phase", help="Phase label recorded in the log entry")
    parser.add_argument("--action", help="Action text recorded in the log entry")
    parser.add_argument("--batch", help="Comma-separated task ids of the current batch")
    parser.add_argument("--task-started", metavar="TN")
    parser.add_argument("--task-done", metavar="TN")
    parser.add_argument(
        "--reconciled",
        metavar="TN[,TN...]",
        help="Task ids where git overrode a tasks.md tick, as printed by detect_phase.py",
    )
    parser.add_argument("--commit", metavar="SHA", help="A commit landed; resets the stall counter")
    parser.add_argument("--gate-attempt", metavar="TN", help="Record one failed gate attempt")
    parser.add_argument("--verify-round", choices=VERDICTS)
    parser.add_argument("--gaps", type=int, help="Gaps left open by the last verify round")
    parser.add_argument("--report", help="Path of the last validation report")
    parser.add_argument("--halt", choices=HALT_REASONS)
    parser.add_argument("--detail", help="Free text explaining the halt")
    parser.add_argument("--status", choices=_state_io.STATUSES)
    parser.add_argument("--objective", help=argparse.SUPPRESS)
    return parser


def apply(state, args):
    """Apply the requested mutations to `state` in place."""
    if args.batch is not None:
        state["current_batch"] = [t.strip() for t in args.batch.split(",") if t.strip()]

    if args.task_started:
        state["current_task"] = args.task_started

    if args.task_done:
        if state.get("current_task") == args.task_done:
            state["current_task"] = None
        # `no_diff_tasks` has no writer. A task that produced no diff is
        # committed empty by `checkpoint.py`, so its completion is a git
        # trailer like any other. The field is kept, and still read by
        # `detect_phase.py`, only so a state written before that change keeps
        # its history.

    if args.reconciled:
        # `tasks.md` ticked a task git does not confirm. Git decided, so the
        # task stays pending; this is the durable record that the plan was
        # overridden rather than believed (LOOP-01 AC 5). Keyed by task id, so
        # re-recording the same disagreement on the next iteration is a no-op.
        recorded = {entry.get("task") for entry in state["reconciled"]}
        for task_id in [t.strip() for t in args.reconciled.split(",") if t.strip()]:
            if task_id in recorded:
                continue
            recorded.add(task_id)
            state["reconciled"].append(
                {"task": task_id, "winner": "git", "at": _state_io.now_iso()}
            )

    if args.gate_attempt:
        attempts = state["counters"].setdefault("gate_attempts", {})
        attempts[args.gate_attempt] = int(attempts.get(args.gate_attempt, 0)) + 1

    if args.verify_round:
        state["verify"]["rounds"] = int(state["verify"].get("rounds") or 0) + 1
        state["verify"]["last_verdict"] = args.verify_round
        # The commit the verification covered. detect_phase compares it against
        # HEAD so a PASS stops counting once the code moves past it (LOOP-04).
        state["verify"]["verified_at"] = _gitio.head_commit(args.root)
    if args.gaps is not None:
        state["verify"]["gaps_open"] = args.gaps
    if args.report is not None:
        state["verify"]["last_report"] = args.report

    if args.halt:
        state["halt"] = {"reason": args.halt, "detail": args.detail}
        state["status"] = "halted"
    # An explicit status is applied last so it wins over the halt default,
    # which is how a proven external blocker becomes `blocked` rather than
    # `halted`.
    if args.status:
        state["status"] = args.status

    if args.commit:
        state["counters"]["iterations_without_commit"] = 0

    if args.iteration_done:
        state["iteration"] = int(state["iteration"]) + 1
        if not args.commit:
            counters = state["counters"]
            counters["iterations_without_commit"] = (
                int(counters.get("iterations_without_commit", 0)) + 1
            )
        state["iterations"].append(
            {
                "n": state["iteration"],
                "at": _state_io.now_iso(),
                "phase": args.phase,
                "action": args.action,
                "task": args.task_done or args.task_started,
                "commit": args.commit,
            }
        )
        # Append-only, then trim the front: history is never rewritten, only
        # forgotten.
        del state["iterations"][:-LOG_LIMIT]

    state["last_updated"] = _state_io.now_iso()
    return state


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.objective is not None:
        print(
            "update_loop: objective is immutable after bootstrap (D12); "
            "refusing to write it",
            file=sys.stderr,
        )
        return 2
    if not any(getattr(args, name) for name in ACTION_FLAGS):
        print("update_loop: nothing to do; pass at least one action flag", file=sys.stderr)
        return 2

    root = os.path.abspath(args.root)
    try:
        state = _state_io.load(args.feature, root)
        _state_io.save(args.feature, root, apply(state, args))
    except _state_io.StateError as exc:
        print(f"update_loop: {exc}", file=sys.stderr)
        return 1

    print(
        f"updated feature={args.feature} iteration={state['iteration']} "
        f"status={state['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
