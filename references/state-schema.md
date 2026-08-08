# `loop.json` schema

The loop's run state. It lives at `.specs/features/<feature>/loop.json` and is
read and written only through `scripts/_state_io.py`, which validates it on the
way in and on the way out.

It is written with `indent=2` and sorted keys, and replaced atomically (temp
file plus rename), so a crash mid-write leaves the previous file intact rather
than a truncated one.

**The file is machine-owned.** Do not hand-edit it. It is also disposable:
deleting it costs the counters and the objective, never task progress.

**It is not committed.** Add `.specs/features/**/loop.json` to the project's
`.gitignore`. The file is a cache: everything durable in it is either
reconstructible from git and `tasks.md`, or a counter that only matters to the
run that is writing it. Committing it is churn on two counts. Every task commit
would carry an unrelated counter bump, which is the opposite of the atomic
one-task diff the checkpoint exists to produce, and the noise lands in exactly
the history a reviewer bisects. `checkpoint.py` stages with `git add -A`
whenever the caller names no paths, so the ignore rule is what keeps the two
apart.

---

## Four invariants

### One writer

Two scripts touch this file and nothing else does:

| Script | What it does |
| --- | --- |
| `init_loop.py` | Creates it, once, at bootstrap. Refuses if it already exists. |
| `update_loop.py` | Every mutation after that. |

`detect_phase.py` only reads: a detect run leaves the file byte-identical.
`checkpoint.py` never opens it at all - it records task completion in git, and
the caller reports that back through `update_loop.py`. Concentrating writes in
one script is what gives the runaway counters a single origin (LOOP-01 AC 6).

### The objective is immutable

`objective` is written verbatim at bootstrap and never changes for the rest of
the run (D12, LOOP-06 AC 5). `update_loop.py` has no route to modify it and
rejects any attempt with a non-zero exit, before reading the file, so a
rejected call cannot half-apply its other flags.

This is also why a corrupt `loop.json` halts instead of being rebuilt:
reconstruction would silently invent a new objective.

### The iteration log is append-only and capped

Entries are only ever appended to `iterations[]`, never edited or reordered.
After each append the array is trimmed to its last **50** entries. History is
forgotten from the front, never rewritten.

### No current phase is stored

There is no `phase` field, deliberately. `detect_phase.py` re-derives the phase
on every run from git trailers, `tasks.md`, and the counters below. A stored
phase would be a second source of truth that could disagree with git, and
resume correctness depends on there being exactly one.

---

## Completed tasks are absent by design

There is no `completed_tasks` field and there will not be one.

Task completion is derived from git on every run, by reading `Task:` commit
trailers (D3, LOOP-01 AC 2):

```
git log --reverse --format="%(trailers:key=Task,valueonly)"
```

Git is authoritative. If a `tasks.md` tick and git history disagree, git wins
and the override lands in `reconciled` below rather than passing silently.
This is exactly what makes the file disposable: delete `loop.json`
mid-run and the next detect still names the same next task, because progress
was never stored here.

The one exception is `no_diff_tasks`, below - the single piece of completion
state git cannot express.

---

## Top-level fields

| Field | Type | Written by | Meaning |
| --- | --- | --- | --- |
| `feature` | string | bootstrap | The feature this run drives. Matches the directory name. |
| `created_at` | string | bootstrap | UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`) when the run was bootstrapped. |
| `last_updated` | string | every write | UTC ISO-8601 of the most recent write. |
| `objective` | string | bootstrap | The run's goal, verbatim from the invocation. Immutable. |
| `status` | string | update | One of `active`, `blocked`, `halted`, `complete`. |
| `iteration` | integer | update | Iterations completed. Incremented exactly once per `--iteration-done`. |
| `harness_resolved` | string | bootstrap | The harness detected at bootstrap, or the one named explicitly. |
| `current_batch` | array of string | update | Task ids in the batch being executed, e.g. `["T8","T9"]`. |
| `current_task` | string or null | update | Task started but not yet committed. `null` between tasks. |
| `no_diff_tasks` | array of string | update | Tasks that legitimately produced no diff. |
| `reconciled` | array of object | update | Tasks where git overrode a `tasks.md` tick. See below. |
| `verify` | object | bootstrap, update | Verification round state. See below. |
| `counters` | object | bootstrap, update | Runaway detectors. See below. |
| `halt` | object | update | Why the run stopped, if it did. See below. |
| `iterations` | array of object | update | The capped iteration log. See below. |

### `status`

| Value | Meaning |
| --- | --- |
| `active` | Running normally. The value set at bootstrap. |
| `blocked` | An external blocker was proven against all three criteria. |
| `halted` | A halt condition fired. Set automatically whenever a halt is recorded. |
| `complete` | The run finished and was verified. |

### `no_diff_tasks`

A config-only or documentation-only task can pass its gate while changing
nothing that git will commit. `checkpoint.py` prints `SKIP: no changes` and
creates no commit, so no `Task:` trailer exists to read back.

Without this list `detect_phase.py` would see the task as pending forever and
re-run it on every iteration. It unions this list with the git trailers to get
the real set of completed tasks. Entries are added once and never removed.

### `reconciled`

The audit trail of git overruling the plan (LOOP-01 AC 5). Each entry:

| Field | Type | Meaning |
| --- | --- | --- |
| `task` | string | The task the two sides disagreed about. |
| `winner` | string | Which side was taken. Always `git`; the field is there so the record reads on its own. |
| `at` | string | UTC ISO-8601 when the override was recorded. |

`tasks.md` has no status field, so the tick on a finished task's header is a
claim rather than an answer. When a ticked task carries no `Task:` trailer,
git wins and the task is dispatched again - and this list is why a later reader
can tell that was a decision and not a bug. An unticked header is not the
opposite claim, so a trailer with no tick records nothing.

`detect_phase.py` finds the disagreement and prints it as `reconciled=<ids>` on
the `phase=B` line; it cannot write, so the loop records it:

```bash
python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> --reconciled T4,T5
```

Entries are keyed by task id, so re-recording the same disagreement on every
iteration until the tick or the history is fixed stores it exactly once.

---

## `verify`

| Field | Type | Meaning |
| --- | --- | --- |
| `rounds` | integer | Verify rounds run so far. Starts at `0`, incremented once per round. |
| `last_verdict` | string or null | `PASS`, `FAIL`, or `null` before the first round. |
| `last_report` | string or null | Path of the most recent `validation.md`. |
| `gaps_open` | integer | Gaps the last FAIL round left unconsumed. |

`detect_phase.py` reads `last_verdict` and `gaps_open` together: a `FAIL`
verdict with `gaps_open > 0` selects `phase=F` (fix), anything else selects
`phase=V` (verify).

`verified_at` holds the commit the last verdict covered, stamped by
`update_loop.py --verify-round`. A PASS closes the feature only while that
commit is still HEAD; anything committed afterwards reopens verification. It is
the one verification fact git cannot supply on its own, which is why it lives
here rather than being derived.

Before either, it compares `rounds` against `verify.max_rounds` from the
config. Reaching the ceiling without a PASS prints
`phase=H action=halt reason=verify_exhausted`, so the escalation is enforced by
the detector rather than remembered by the loop. An omitted `max_rounds` is
unlimited and never halts.

---

## `counters`

The runaway detectors. Every value here is compared against a `[limits]` key
from `loop.config.toml`, and an omitted limit is unlimited, so a counter can
grow without ever firing.

| Field | Type | Meaning |
| --- | --- | --- |
| `started_at_ms` | integer | Unix epoch milliseconds at bootstrap. Written once and never updated; `max_minutes` is measured from it. |
| `iterations_without_commit` | integer | Iterations closed since the last recorded commit. |
| `gate_attempts` | object | Map of task id to failed gate attempts, e.g. `{"T11": 2}`. |

### `iterations_without_commit`

Resets to `0` whenever a commit is recorded, and increments whenever an
iteration closes without one. It backs the `no_progress` halt (LOOP-06 AC 6):
if the loop keeps iterating but nothing lands in git, something is wrong with
detection or dispatch and the run should stop rather than spin.

A task that produced no diff records no commit, so it increments this counter
like any other commitless iteration.

### `gate_attempts`

Counts *failed* gate attempts per task, backing the `gate_stuck` halt
(LOOP-06 AC 7). Keys appear the first time a task's gate fails; a task whose
gate passes first time never appears.

---

## `halt`

| Field | Type | Meaning |
| --- | --- | --- |
| `reason` | string or null | Halt reason slug, or `null` while the run is live. |
| `detail` | string or null | Free text explaining the halt. |

A recorded halt outranks everything: `detect_phase.py` checks it before it
describes any work, so a halted run never dispatches another batch.

| `reason` | Fires when |
| --- | --- |
| `no_progress` | No commit across `no_progress_iterations` iterations. |
| `gate_stuck` | One task's gate failed more than `gate_attempts_per_task` times. |
| `executor` | An executor failed to launch, lost authentication, hit a quota, or timed out. |
| `limit` | `max_iterations` or `max_minutes` was reached. |
| `blocker` | An external blocker was proven, or the tree holds changes mapping to no task. |
| `blast_radius` | A push, deploy, or other remote or destructive operation is required. |

`state_corrupt` is **not** in this table and is never stored. `detect_phase.py`
prints it when `loop.json` itself cannot be parsed, which is precisely the
situation where nothing can be written to record it.

---

## `iterations[]`

Append-only, capped at the last 50. Each entry:

| Field | Type | Meaning |
| --- | --- | --- |
| `n` | integer | The value of `iteration` after this one closed. |
| `at` | string | UTC ISO-8601 when the iteration closed. |
| `phase` | string or null | Phase label the iteration ran, e.g. `B`. |
| `action` | string or null | Short description of what it did. |
| `task` | string or null | Task finished, or failing that the task started. |
| `commit` | string or null | SHA recorded for this iteration, if one landed. |

The log is an audit trail, not state the loop reads back. Nothing derives a
decision from it, which is why trimming old entries is safe.

---

## Full example

```json
{
  "feature": "auth-refresh",
  "created_at": "2026-08-08T12:00:00Z",
  "last_updated": "2026-08-08T14:31:07Z",
  "objective": "ship auth-refresh end to end",
  "status": "active",
  "iteration": 14,
  "harness_resolved": "claude",

  "current_batch": ["T8", "T9", "T10"],
  "current_task": "T9",
  "no_diff_tasks": ["T4"],

  "verify": {
    "rounds": 1,
    "last_verdict": "FAIL",
    "last_report": ".specs/features/auth-refresh/validation.md",
    "gaps_open": 2
  },

  "counters": {
    "started_at_ms": 1786000000000,
    "iterations_without_commit": 0,
    "gate_attempts": { "T9": 2 }
  },

  "halt": { "reason": null, "detail": null },

  "iterations": [
    {
      "n": 14,
      "at": "2026-08-08T14:31:07Z",
      "phase": "B",
      "action": "execute batch P2",
      "task": "T8",
      "commit": "a1b2c3d"
    }
  ]
}
```
