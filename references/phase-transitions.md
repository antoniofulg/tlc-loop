# Phase transitions

The contract of `scripts/detect_phase.py`: what it can print, when it prints
it, and what has to become true before the loop leaves each phase.

```
detect_phase.py <feature> [--root DIR]
```

Run it at the start of every iteration and do what the line says.

---

## Two properties the rest of the contract rests on

### It prints exactly one line

One invocation, one line on stdout, always from the vocabulary below. Never
zero lines, never two. A run that cannot describe the situation prints nothing
on stdout, writes the reason to stderr, and exits 1.

### It writes nothing

No file is created or modified, no commit is made, no counter is bumped.
`git status --porcelain` and `loop.json` are byte-identical before and after,
so the script is safe to run for inspection at any moment, as many times as you
like. Counters are advanced by `update_loop.py`, never here.

The consequence worth internalising: **there is no stored current phase.** The
phase is re-derived from evidence on every run. That is what makes an
interrupted run resume correctly, and it is why task progress is the one thing
deleting `loop.json` does not cost. It costs everything else in the file;
`state-schema.md` itemises the bill.

---

## Output vocabulary

Every line the implementation can print, with the condition that produces it.

| Line | Entry condition |
| --- | --- |
| `phase=0 action=bootstrap` | `loop.json` does not exist for this feature. |
| `phase=H action=halt reason=<slug> detail="<text>"` | A halt condition holds. Checked before any work is described. |
| `phase=B action=execute_batch batch=<label> tasks=<ids>` | At least one planned task is not yet done. |
| `phase=E action=done` | Nothing pending, `validate_state.py` exits 0, and the recorded verdict still covers HEAD. |
| `phase=F action=fix round=<N>` | Nothing pending, not done, the last verdict was `FAIL` and gaps are still open. |
| `phase=V action=verify round=<N>` | Nothing pending, not done, and no open gaps to fix. |

Every line except a halt can trail **advisory fields**: `reconciled=<ids>` then
`dup=<ids>`, in that order, each present only when it has something to say.
They report what the detector observed on the way to its answer - they never
change the answer. A halt line never carries them: its contract is `reason`
plus `detail`, and nothing follows a halt that could act on the observation.

### Field shapes

- `batch=<label>` is the batch's phases joined with `+`: `P1`, `P1+P2`,
  `P3+P4+P5`. A batch always holds consecutive whole phases.
- `tasks=<ids>` is the batch's task ids, comma separated, no spaces:
  `T1,T2,T3`. The ids are explicit on purpose. Phase labels alone become
  ambiguous the moment `tasks.md` is edited, and the transcript is what an
  external evaluator reads.
- `round=<N>` on `phase=V` is the verify round about to run:
  `verify.rounds + 1`.
- `round=<N>` on `phase=F` is the round whose gaps are being fixed:
  `verify.rounds`. A fix belongs to the round that found the gaps, so `V round=2`
  following `F round=1` reads as one cycle rather than two.
- `reconciled=<ids>` lists, comma separated, the tasks a human ticked in
  `tasks.md` that git does not confirm. Present only when there is at least
  one, and only on `phase=B`: a task git has not confirmed is by definition
  still pending, so no other line can carry it. It is advisory - git has
  already decided and the task is in the batch like any other - and it exists
  so the override can be recorded rather than passing silently.
- `dup=<ids>` lists, comma separated, the tasks whose `Task:` trailer appears
  on more than one commit, each named once however many copies exist. It is a
  property of history rather than of the plan, so it can ride any non-halt
  line - including `phase=V` and `phase=E`, long after the last batch.
- `reason=<slug>` is one of `no_progress`, `gate_stuck`, `executor`, `limit`,
  `blocker`, `blast_radius`, `state_corrupt`, `verify_exhausted`.
- `detail="<text>"` is always present on a halt line, always double quoted,
  always a single line. Internal double quotes become single quotes and runs of
  whitespace collapse, so the line stays parseable by a shell driver.

---

## Derivation order

Each step runs only if the previous one did not print. This order is the
contract, not an implementation detail.

1. **No `loop.json`** → `phase=0`. Nothing else is read.
2. **Load `loop.json`.** Unreadable → `phase=H reason=state_corrupt`, with the
   codec's own message as the detail. Then load `loop.config.toml`; that one
   failing to parse exits 1.
3. **Halt check** → `phase=H`. See the precedence below.
4. **Derive what is done.** `git log --reverse --format="%(trailers:key=Task,valueonly)"`,
   deduped, unioned with `no_diff_tasks` from `loop.json`.
5. **Derive the plan.** Task ids and phases parsed from `tasks.md`. A missing
   `tasks.md` exits 1.
6. **`pending = planned - done`.** Non-empty → `phase=B`, packing the pending
   tasks into batches of whole phases up to `execute.batch_size` and naming the
   first one.
7. **Ask the validator, then ask how old its answer is.** `validate_state.py`
   exiting 0 says the report reads PASS with evidence. It cannot say whether
   the report describes *this* code. So the PASS counts only while
   `verify.verified_at` - the commit stamped onto the verdict by
   `update_loop.py --verify-round` - is still HEAD. Both true → `phase=E`.

   A commit landing after a PASS therefore returns detection to `phase=V`
   rather than closing the feature: otherwise a task would ship as verified
   with no verifier having seen it. An absent `verified_at` counts as
   uncovered - after a rebuilt `loop.json`, for instance - which costs one
   verify round and never declares an unverified tree done.
8. **Check the verify budget.** `verify.rounds` having reached
   `verify.max_rounds` → `phase=H reason=verify_exhausted`. An absent
   `max_rounds` is unlimited and never fires.
9. **Otherwise** → `phase=F` when the last verdict was `FAIL` with
   `gaps_open > 0`, else `phase=V`.

### Git wins over state

Step 4 is the one to be precise about. Commit trailers are authoritative. When
`loop.json` and git disagree about a task, git decides and `loop.json` is
treated as the stale side. A task recorded as `current_task` in state but
already carrying a `Task:` trailer in git is **done**, not in flight.

The plan can disagree out loud. `tasks.md` has no status field, so the tick a
human leaves on a finished task's header is a claim, and a claim git does not
confirm is a contradiction. Git wins: the task stays pending and is dispatched
again. The contradiction is not swallowed - the ids ride the `phase=B` line as
`reconciled=<ids>`, and the loop records them with
`update_loop.py --reconciled <ids>`, which appends one entry per task naming
the winning side (LOOP-01 AC 5). Recording is idempotent, so a disagreement
that survives several iterations is stored once. The reverse case is not a
contradiction: an unticked header claims nothing, so a trailer without a tick
just means the plan was never annotated.

`no_diff_tasks` is not an exception to this rule. It is the one piece of
completion state git cannot express: a config-only or docs-only task that
legitimately produced no commit, and therefore no trailer. Without the union
such a task would be re-dispatched forever. It is additive only, and it can
never mark a task incomplete that git says is complete.

A duplicate `Task:` trailer, which a rebase or cherry-pick can leave behind,
counts once. The duplication is reported rather than dropped: `_gitio` hands
the ids back alongside the deduped ones, and they trail the line as
`dup=<ids>`. Reporting is all that is owed - the task is complete either way,
so the run continues - but a task id that shows up twice in history is a sign
somebody rewrote commits, and the transcript says so.

### Absent state bootstraps, unreadable state halts

Step 1 and step 2 look similar and are deliberately opposite.

An **absent** `loop.json` keeps task progress and loses the rest: bootstrap
writes a fresh file and the next detect re-derives the same next task from git
and `tasks.md`, but the objective is re-supplied unchecked, every limit budget
restarts, one verification is owed, and a recorded halt is gone.
`state-schema.md` itemises it. Reconstruction is *allowed* because the run can
continue from it, not because it is free.

An **unreadable** one is different. The bytes exist, so something is in there -
possibly the objective a run has been driving toward for eight hours - and the
codec cannot tell a truncated write from a hand edit. Overwriting it with a
reconstruction would discard that silently. So the run stops:
`phase=H action=halt reason=state_corrupt detail="<the codec's message>"`.

Unreadable means anything `_state_io.load` rejects: malformed JSON, a missing
required key, an unknown `status`. All of them mean the same thing operationally
- the state cannot be read - so they carry one reason. Deleting the file
deliberately is the documented way out, and it lands on the absent branch above.

The halt exits 0 like every other phase line. A raw non-zero exit here would
force `loop.sh`, a goal evaluator, and the in-turn motor to each special-case
one situation the vocabulary already covers.

### Halt is checked first

Step 3 sits ahead of every derivation that describes work. A run that must stop
must not first be told to execute a batch, because the line the loop acts on is
the line it prints. Ordering the halt check last would mean a halted run still
dispatches one more batch.

Within the halt check the order is fixed, so the answer is reproducible:

1. A halt already recorded in `loop.json` (`halt.reason` is set). Its reason and
   detail are printed verbatim.
2. `status` is `blocked` → `blocker`.
3. `iterations_without_commit` has reached `limits.no_progress_iterations` →
   `no_progress`.
4. Any task's gate attempts exceed `limits.gate_attempts_per_task` →
   `gate_stuck`, naming the task.
5. `iteration` has reached `limits.max_iterations` → `limit`.
6. Elapsed time has reached `limits.max_minutes` → `limit`.

**A limit absent from the config is unlimited and never fires.** TOML has no
`null`, so omission is the only way to express "no limit", and a detector whose
limit is unset is skipped entirely rather than defaulted to some number.

### The verify budget is checked late, not with the others

`verify_exhausted` is the one halt that is not part of the block above. It sits
at step 8, after the validator has been asked, for two reasons.

A PASS must win. The condition is "the rounds are spent **without a PASS**", so
a feature that verified successfully on its last available round is done, not
halted. Asking the validator first is what makes that true.

Pending work must win too. The ceiling exists to stop verify and fix rounds
from repeating forever; it says nothing about a batch that has not run yet. A
`tasks.md` that grows a task after a failed verify round still gets that task
executed, and only then runs into the ceiling.

What it must come before is the round it would authorise. Both `phase=V` and
`phase=F` spend from the same budget, so the check sits ahead of both: an
exhausted loop never dispatches one more round of either.

---

## Exit rules per phase

What has to become true before detection stops returning the same line.

| Phase | Leaves when |
| --- | --- |
| `0` | `init_loop.py` has written `loop.json`. The next detect re-derives from git, so bootstrap never decides what to work on. |
| `B` | Every task in the batch carries a `Task:` trailer, or is recorded in `no_diff_tasks`. The batch is not "done" because a worker said so; it is done because the trailers exist. |
| `V` | A verdict is recorded: `PASS` closes the feature, `FAIL` with open gaps moves to `F`. |
| `F` | The gaps are consumed (`gaps_open` back to 0), which returns detection to `V` for a fresh round. |
| `E` | Terminal. Nothing follows. Print the done-signature and stop. |
| `H` | Terminal for this run. A halt clears only by a human resolving the cause and clearing `halt.reason`, or by changing the config that tripped a limit. Re-invoking without changing anything prints the same halt line. |

`E` and `H` are the only terminal phases. Everything else re-enters detection.

Two of these deserve emphasis:

- **`B` never advances on a claim.** An executor reporting success is not
  evidence. The trailer is. This is what makes the loop resumable after a crash
  mid-batch: whatever was really committed stays done, and the rest is
  re-derived as pending.
- **`H` does not clear itself.** Halting is halting, not asking. With nobody
  watching, a prompt is the same as a hang, so the run stops and records why.

---

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | A line was printed describing the situation. Includes `phase=H`: a halt is a described situation, not a script failure. |
| `1` | The situation could not be read. Nothing on stdout, reason on stderr. |

Exit 1 covers: `loop.config.toml` unparseable, `tasks.md` missing, the root not
being a git repository, and the sibling `tlc-spec-driven` skill not being
resolvable. All four are the user's files or the user's install, fixed by
editing something outside the run.

`loop.json` being unparseable is **not** in that list. It is machine state, so
it belongs to the run, and it is reported as `phase=H reason=state_corrupt`
with exit 0.

A halt is deliberately not an exit code. `loop.sh`, a goal evaluator, and the
in-turn motor all read the same one-line contract, so a halt reason expressed
in that vocabulary needs one parser instead of three.
