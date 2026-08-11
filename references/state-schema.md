# `loop.json` schema

The loop's run state. It lives at `.specs/features/<feature>/loop.json` and is
read and written only through `scripts/_state_io.py`, which validates it on the
way in and on the way out.

It is written with `indent=2` and sorted keys, and replaced atomically (temp
file plus rename), so a crash mid-write leaves the previous file intact rather
than a truncated one.

**The file is machine-owned.** Do not hand-edit it. Deleting it costs
everything in it except task completion, which lives in git. The full bill is
[below](#what-deleting-the-file-costs); it is larger than it looks.

**It is not committed.** Add `.specs/features/**/loop.json` to the project's
`.gitignore`. Nothing in it belongs to the project: it is one run's private
bookkeeping, and the next run's is different. Committing it is churn on two
counts. Every task commit
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

So task progress is the one thing the file can lose without losing anything:
delete `loop.json` mid-run and the next detect prints
`phase=0 action=bootstrap`; re-bootstrap and it names the same task, because
progress was never stored here. A task that changed nothing is included too -
see [the no-diff contract](#the-no-diff-contract).

## What deleting the file costs

Everything else. Nothing below is reconstructible from git, and re-bootstrapping
restores none of it:

| Lost | Consequence |
| --- | --- |
| `objective` | Re-supplied at bootstrap, and nothing checks the new one against the old. A rebuilt run can be driving at a different target. |
| `counters` | Every `[limits]` budget restarts, including the `max_minutes` clock measured from `started_at_ms`. A run near a limit walks away from it. |
| `verify.rounds`, `epoch_rounds`, `last_verdict`, `gaps_open` | The `verify.max_rounds` budget restarts, so a run that was one round from `verify_exhausted` gets a full new allowance. |
| `verify.verified_at` | The rebuilt state owes one verification round; no verdict covers HEAD any more, whatever the report on disk says. |
| `halt` | A recorded halt is cleared. A run that stopped for a reason resumes as if it had not. |
| `reconciled`, `iterations` | The audit trails. Nothing derives a decision from them, but the record of what happened is gone. |
| `no_diff_tasks` | Legacy, and empty on any run bootstrapped after T37. A run already in flight when T37 landed loses the entries it wrote. |

Deleting the file is therefore a deliberate act with a price, not a reset
button. It is still the documented way out of a corrupt state file - see
[phase-transitions.md](phase-transitions.md) - because a halt you can explain
beats a state nobody can read.

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
| `no_diff_tasks` | array of string | nothing | Legacy; still read. See [the no-diff contract](#the-no-diff-contract). |
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
| `complete` | The run finished and was verified. `update_loop.py` refuses to write it unless the recorded PASS still covers HEAD, so the field cannot outlive its evidence. |

### The no-diff contract

**This section is the skill's only full description of what happens to a task
that changes nothing. Every other mention links here instead of restating it.**
That rule exists because the restatements drifted: the same claim shipped false
four times, each time in a document that had been correct when it was written.
One description cannot disagree with itself.

A config-only or documentation-only task can pass its gate while changing
nothing git would commit. It is committed anyway. `checkpoint.py` stages, finds
an empty index, and commits with `--allow-empty`, carrying the same `Task:` and
`Gate:` trailers as every other task; the line it prints ends `PASS empty`.

Three consequences follow, and together they are the reason for the design:

- **Completion lives in git for every task, without exception.** The trailer is
  the record, so `detect_phase.py` reads such a task back like any other and
  deleting `loop.json` cannot re-dispatch it.
- **No source diff is fabricated** (LOOP-02 AC 6). An empty commit has none: it
  carries the trailers and nothing else.
- **It is a commit like any other.** The task records one, so it resets
  `iterations_without_commit` exactly as a task that touched a file does. It is
  not a commitless iteration and contributes nothing to `no_progress`.

`no_diff_tasks` is the legacy of what this replaced (T37), when such a task was
recorded in `loop.json` and nowhere else - the one place git cannot rebuild, so
deleting the file re-dispatched a finished task. Nothing writes the field now.
`detect_phase.py` still unions it with the git trailers so a run already in
flight keeps the entries it wrote; a new run leaves it empty.

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
| `rounds` | integer | Verify rounds run so far, for the life of the run. Starts at `0`, incremented once per round. |
| `epoch_rounds` | integer | Rounds run in the current verification epoch. What `verify.max_rounds` bounds. |
| `last_verdict` | string or null | `PASS`, `FAIL`, or `null` before the first round. |
| `last_report` | string or null | Path of the most recent `validation.md`. |
| `gaps_open` | integer | Gaps the last FAIL round left unconsumed. |
| `verified_at` | string or null | Full SHA of the commit the last verdict covered. |

`detect_phase.py` reads `last_verdict` and `gaps_open` together: a `FAIL`
verdict with `gaps_open > 0` selects `phase=F` (fix), anything else selects
`phase=V` (verify).

`verified_at` is stamped by `update_loop.py --verify-round`. It is the one
verification fact git cannot supply on its own, which is why it lives here
rather than being derived - and it is the input to the coverage rule that
decides whether a PASS still describes the tree.

**Coverage, the seal, and what an epoch is are specified once, in
[verification-freshness.md](verification-freshness.md).** Nothing about them is
restated here; the fields above are the storage, not the contract.

Before naming a round, the detector compares `epoch_rounds` against
`verify.max_rounds` from the config. Reaching the ceiling without a PASS prints
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

A task that changed nothing is not a commitless iteration: it is committed
empty, so it resets this counter like any other task. See
[the no-diff contract](#the-no-diff-contract).

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
    "rounds": 4,
    "epoch_rounds": 1,
    "last_verdict": "FAIL",
    "last_report": ".specs/features/auth-refresh/validation.md",
    "gaps_open": 2,
    "verified_at": "1f0c2e9a4b7d8c5e3a1b9f7d2c4e6a8b0d3f5c71"
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
