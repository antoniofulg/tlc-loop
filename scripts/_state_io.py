"""Strict read/write codec for `loop.json` - the only module that touches it.

`loop.json` is machine-owned with a single writer (LOOP-01 AC 5), so the codec
is deliberately unforgiving: anything it did not write itself is a corruption
signal, not something to repair silently. Completed tasks are absent by design
(D3) - they are derived from git trailers on every run, which is why losing
this file costs no task progress. It costs everything else in the file; see
`references/state-schema.md`.

State lives at `<root>/.specs/features/<feature>/loop.json`.

Imported, never invoked directly.
"""

import json
import os
import time
from datetime import datetime, timezone

STATUSES = ("active", "blocked", "halted", "complete")

REQUIRED_KEYS = (
    "feature",
    "created_at",
    "last_updated",
    "objective",
    "status",
    "iteration",
    "harness_resolved",
    "current_batch",
    "current_task",
    "no_diff_tasks",
    "reconciled",
    "verify",
    "counters",
    "halt",
    "iterations",
)


class StateError(Exception):
    """`loop.json` is missing, unparseable, or violates the documented schema."""


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(feature, root):
    """Absolute path of the state file for a feature."""
    return os.path.join(os.path.abspath(root), ".specs", "features", feature, "loop.json")


def new_state(feature, objective, harness):
    """The documented initial shape. `objective` is immutable from here (D12)."""
    stamp = now_iso()
    return {
        "feature": feature,
        "created_at": stamp,
        "last_updated": stamp,
        "objective": objective,
        "status": "active",
        "iteration": 0,
        "harness_resolved": harness,
        "current_batch": [],
        "current_task": None,
        # Legacy: read by detect_phase.py so a pre-T37 state keeps its history,
        # written by nothing. A new run leaves it empty for good.
        "no_diff_tasks": [],
        "reconciled": [],
        "verify": {"rounds": 0, "last_verdict": None, "last_report": None,
                   "gaps_open": 0, "verified_at": None},
        "counters": {
            "started_at_ms": int(time.time() * 1000),
            "iterations_without_commit": 0,
            "gate_attempts": {},
        },
        "halt": {"reason": None, "detail": None},
        "iterations": [],
    }


def _validate(state, where):
    if not isinstance(state, dict):
        raise StateError(f"{where}: expected a JSON object, got {type(state).__name__}")
    missing = [k for k in REQUIRED_KEYS if k not in state]
    if missing:
        raise StateError(f"{where}: missing required key(s): {', '.join(missing)}")
    status = state["status"]
    if status not in STATUSES:
        raise StateError(
            f"{where}: unknown status {status!r}; expected one of {', '.join(STATUSES)}"
        )
    for key in ("verify", "counters", "halt"):
        if not isinstance(state[key], dict):
            raise StateError(f"{where}: {key} must be an object")
    for key in ("current_batch", "no_diff_tasks", "reconciled", "iterations"):
        if not isinstance(state[key], list):
            raise StateError(f"{where}: {key} must be a list")
    if not isinstance(state["iteration"], int) or isinstance(state["iteration"], bool):
        raise StateError(f"{where}: iteration must be an integer")
    return state


def load(feature, root):
    """Parse and schema-validate `loop.json`. Raises StateError on anything else."""
    path = state_path(feature, root)
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise StateError(f"{path}: no such file") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"{path}: malformed JSON: {exc}") from exc
    return _validate(raw, path)


def save(feature, root, state):
    """Validate, then write atomically (temp file + rename) with stable formatting."""
    path = state_path(feature, root)
    _validate(state, path)
    # Serialise fully before touching the filesystem so a serialisation failure
    # cannot leave a half-written temp file behind.
    text = json.dumps(state, indent=2, sort_keys=True) + "\n"
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
