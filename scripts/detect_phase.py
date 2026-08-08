#!/usr/bin/env python3
"""detect_phase.py - the single answer to "what happens next". Read-only.

Prints exactly one line describing the next action, then exits. The loop calls
this at the start of every iteration and does what the line says.

Nothing here writes. No file is created or modified, no commit is made, no
counter is bumped, so the script can be run freely for inspection and a run
leaves `git status --porcelain` and `loop.json` byte-identical.

There is no stored "current phase". The phase is re-derived every run from git
trailers, `tasks.md`, and the `loop.json` counters, which is what makes an
interrupted run resume at the right place: deleting `loop.json` costs counters
and the objective, never task progress.

Usage:
    detect_phase.py <feature> [--root DIR]

Output vocabulary (exactly one of these, on stdout):
    phase=0 action=bootstrap
    phase=B action=execute_batch batch=P1+P2 tasks=T1,T2,T3
    phase=V action=verify round=N
    phase=F action=fix round=N
    phase=E action=done
    phase=H action=halt reason=<slug> detail="<text>"

An unreadable `loop.json` is not one of those failures: it is a halt with
`reason=state_corrupt`, printed on stdout like any other phase line.

Exit codes: 0 the line describes the situation, 1 the situation could not be
read (unparseable config, missing tasks.md, no repository, sibling skill
missing) with the reason on stderr and nothing on stdout.
"""

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _batching  # noqa: E402
import _config  # noqa: E402
import _gitio  # noqa: E402
import _paths  # noqa: E402
import _state_io  # noqa: E402
import _tasksmd  # noqa: E402


def _quote(text):
    """Render a halt detail as one double-quoted token."""
    flat = " ".join(str(text or "").split())
    return '"' + flat.replace('"', "'") + '"'


def _tasks_path(root, feature):
    return os.path.join(root, ".specs", "features", feature, "tasks.md")


def halt_reason(state, config):
    """Return `(reason, detail)` for the first halt condition that holds.

    Order is fixed so the answer is reproducible: an already-recorded halt, a
    blocked run, then the runaway detectors, then the hard limits. A limit that
    is absent from the config is unlimited and never fires.
    """
    halt = state.get("halt") or {}
    if halt.get("reason"):
        return halt["reason"], halt.get("detail") or ""

    if state.get("status") == "blocked":
        return "blocker", "run is recorded as blocked"

    limits = config["limits"]
    counters = state.get("counters") or {}

    ceiling = limits.get("no_progress_iterations")
    stalled = counters.get("iterations_without_commit", 0)
    if ceiling is not None and stalled >= ceiling:
        return "no_progress", f"no commit across {stalled} iterations, limit {ceiling}"

    ceiling = limits.get("gate_attempts_per_task")
    if ceiling is not None:
        for task, attempts in sorted((counters.get("gate_attempts") or {}).items()):
            if attempts > ceiling:
                return "gate_stuck", f"{task} gate failed {attempts} times, limit {ceiling}"

    ceiling = limits.get("max_iterations")
    if ceiling is not None and state.get("iteration", 0) >= ceiling:
        return "limit", f"reached max_iterations {ceiling}"

    ceiling = limits.get("max_minutes")
    started = counters.get("started_at_ms")
    if ceiling is not None and started:
        elapsed = (time.time() * 1000 - started) / 60000.0
        if elapsed >= ceiling:
            return "limit", f"reached max_minutes {ceiling}"

    return None, None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="detect_phase.py", description="Print the loop's next action. Read-only."
    )
    parser.add_argument("feature")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    feature = args.feature

    # 1. No state file: nothing has been set up yet.
    if not os.path.isfile(_state_io.state_path(feature, root)):
        print("phase=0 action=bootstrap")
        return 0

    # 1b. The state file exists but cannot be read. That is a situation, not a
    #     script failure: it is reported in the same phase vocabulary as every
    #     other stop, so no consumer has to special-case a raw exit code.
    #     Reconstructing from git instead would silently discard the immutable
    #     objective, which is why an unreadable file halts where an absent one
    #     bootstraps (LOOP-01 AC 3 and AC 4).
    try:
        state = _state_io.load(feature, root)
    except _state_io.StateError as exc:
        print(f"phase=H action=halt reason=state_corrupt detail={_quote(exc)}")
        return 0

    # The config is user-owned rather than machine state, so a malformed one is
    # a plain error the user fixes by editing the file.
    try:
        config = _config.load_config(root)
    except _config.ConfigError as exc:
        print(f"detect_phase: {exc}", file=sys.stderr)
        return 1

    # 2. A halt outranks any work, so it is answered before work is described.
    reason, detail = halt_reason(state, config)
    if reason:
        print(f"phase=H action=halt reason={reason} detail={_quote(detail)}")
        return 0

    # 3. Git is authoritative for what is done; no_diff_tasks covers the tasks
    #    that legitimately produced no commit.
    try:
        committed, _duplicates = _gitio.completed_tasks(root)
    except _gitio.GitError as exc:
        print(f"detect_phase: {exc}", file=sys.stderr)
        return 1
    done = set(committed) | set(state.get("no_diff_tasks") or [])

    # 4. The plan.
    tasks_path = _tasks_path(root, feature)
    if not os.path.isfile(tasks_path):
        print(f"detect_phase: no tasks.md at {tasks_path}", file=sys.stderr)
        return 1
    planned = _tasksmd.parse(tasks_path)

    # 5. Work remains: name the next batch and the exact tasks in it.
    pending = [task for task in planned if task["id"] not in done]
    if pending:
        batches, _oversized = _batching.pack(pending, config["execute"]["batch_size"])
        batch = batches[0]
        label = "+".join(f"P{phase}" for phase in batch["phases"])
        print(
            f"phase=B action=execute_batch batch={label} "
            f"tasks={','.join(batch['tasks'])}"
        )
        return 0

    # 6. Nothing pending. The sibling validator decides whether this is done.
    try:
        validator = _paths.tlc_script("validate_state.py")
    except _paths.SiblingSkillError as exc:
        print(f"detect_phase: {exc}", file=sys.stderr)
        return 1
    finished = subprocess.run(
        [sys.executable, validator, feature, "--root", root],
        capture_output=True,
        text=True,
    )
    if finished.returncode == 0:
        print("phase=E action=done")
        return 0

    # 7. Not done: fix the gaps a FAIL round left open, else verify again.
    verify = state.get("verify") or {}
    rounds = int(verify.get("rounds") or 0)
    if verify.get("last_verdict") == "FAIL" and int(verify.get("gaps_open") or 0) > 0:
        print(f"phase=F action=fix round={rounds}")
        return 0
    print(f"phase=V action=verify round={rounds + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
