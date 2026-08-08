---
name: tlc-loop
description: Unattended execution loop for an approved tlc-spec-driven tasks.md: detects the phase from git commit trailers, dispatches batches to per-stage configurable providers, commits each task atomically, repairs its own failures, and halts with a recorded reason instead of stalling. Use when running a formal tasks.md to a verified PASS without per-batch prompting, or resuming a run that was interrupted. Another skill reaches it when tlc-spec-driven delegates Execute to loop mode. Triggers on "run the loop" and "resume the loop". Do NOT use for a single task, for a feature with no formal tasks.md, or for Specify, Design, or Tasks authoring - those stay interactive in tlc-spec-driven.
license: CC-BY-4.0
metadata:
  version: 0.1.0
---

# Unattended Execution Loop

Drive an approved `tasks.md` to a verified PASS without per-batch prompting.
Each iteration detects the current phase, runs exactly one phase action,
records it, prints a summary, and **continues** at detect. It stops for a
reason it writes down, never by drifting to a halt.

This skill sequences and enforces. `tlc-spec-driven` still defines what a task
cycle is, what a good test is, and what verification means. Nothing is
reimplemented here.

| Phase | Action | Terminal |
| --- | --- | --- |
| `0` | bootstrap: check preconditions, write `loop.json` once | no |
| `B` | execute one batch of tasks, gate each, checkpoint each | no |
| `V` | independent verification, read-only | no |
| `F` | fix the ranked gaps from a FAIL round | no |
| `E` | done: print the done-signature | **yes** |
| `H` | halt: a recorded reason, nothing more happens | **yes** |

## Not this skill's job

- **Specify, Design, and Tasks stay interactive.** The loop starts at a
  `tasks.md` that already passes `validate_tasks.py`. Human review pays off
  most on hard-to-reverse decisions.
- **A single task.** Use `tlc-spec-driven` directly. The loop's machinery costs
  more than it saves below one batch.
- **A feature with no formal `tasks.md`.** Bootstrap refuses.
- **Anything remote.** See the blast-radius rule below.

---

## Critical rules

**Resolving this skill's own files.** `references/` and `scripts/` live under
this skill's directory, the one holding this `SKILL.md`. Resolve it with
`realpath` and invoke scripts by that absolute path. Never run
`python3 scripts/...` from the consuming project root: that looks for a
project-local `scripts/` tree which is not this skill. Below, `<skill-dir>` is
this skill's directory and `<root>` is the project root containing `.specs/`.
Project data under `.specs/` is always read and written relative to `<root>`,
which is what `--root` carries.

**Git is the status truth.** Completed tasks come from
`git log --format="%(trailers:key=Task,valueonly)"`. A task that changed
nothing is committed empty, so it carries a trailer like any other. When
`loop.json` and git disagree, git wins. This is what makes resume correct.

**Two single writers, no exceptions.** `checkpoint.py` is the only writer of
git trailers. `update_loop.py` is the only writer of `loop.json` after
bootstrap. Never hand-edit `loop.json`, and never commit outside
`checkpoint.py`.

**An executor never commits, and its evidence is never trusted.** Both rules
are stated verbatim in every payload. Read
[executors.md](references/executors.md) in full before building any payload.

**Gate first, record second.** A `Task:` trailer means the gate passed. Never
weaken an assertion, delete a test, or skip one to get a gate green, and never
pass git a flag that bypasses a hook.

**Blast radius halts and waits.** Approving a spec and a `tasks.md` authorizes
local implementation and local commits, nothing else. When the work needs
`git push`, a force-push, a deploy, a production data change, or any other
remote or destructive operation, record the halt and stop:

```bash
python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> \
  --halt blast_radius --detail "<the operation that needs authorization>"
```

**Do not ask and proceed.** An unattended run has nobody to answer a prompt, so
a question and a hang are the same event. A recorded halt is resumable the
moment a human reads it; a prompt sits on a pipe until someone kills it.

**Every failure is repairable by default.** Read
[recovery-loop.md](references/recovery-loop.md) in full the moment anything
exits non-zero. An intermediate failure stays inside the phase action: it does
not close an iteration and does not print a summary.

---

## Inputs

- `<feature>` - the directory name under `.specs/features/`.
- `<objective>` - the run's success criterion, in the user's own words. Written
  verbatim at bootstrap and immutable afterwards, so the run cannot redefine
  what "done" means halfway through.
- `--respawn <provider>` - optional. Names the running harness instead of
  detecting it. Required whenever detection is inconclusive.

## Helper scripts

Under `<skill-dir>/scripts/`. Stdlib-only Python 3.11+ and one bash script. No
network, no model calls.

| Script | Role | Phase |
| --- | --- | --- |
| `init_loop.py` | bootstrap; writes `loop.json` exactly once | 0 |
| `detect_phase.py` | read-only; prints the next action | every iteration |
| `update_loop.py` | the only mutator of `loop.json` | every iteration |
| `checkpoint.py` | mutating; the atomic per-task commit and its trailers | B, F |
| `resolve_stage.py` | read-only; turns a configured stage into a concrete invocation | B, V, F |
| `loop.sh` | mutating; spawns the respawn agent across turns | continuation |
| `_paths` `_state_io` `_config` `_gitio` `_tasksmd` `_batching` | support modules | imported, never invoked |

From the sibling `tlc-spec-driven`, resolved through `_paths.tlc_script()`:
`validate_tasks.py` gates bootstrap, `check_commit.py` gates every commit
message, `validate_state.py` decides phase E, and `lessons.py` distils grounded
failures after a FAIL round.

## Configuration

`.specs/loop.config.toml` is optional and entirely defaulted when absent.
Schema: [config-schema.md](references/config-schema.md). Starter file:
[loop.config.example.toml](assets/loop.config.example.toml).

The loop **reads** it and never writes it. Runtime-resolved values go to
`loop.json`. Under `[limits]`, an omitted key means unlimited.

---

## Workflow

One **iteration** is: detect, one phase action, record, summarize, continue.

### Step 1 - Detect

```bash
python3 <skill-dir>/scripts/detect_phase.py <feature> --root <root>
```

Exactly one line, always. Run it first, every iteration, and do what it says.
It writes nothing, so it is safe to run for inspection at any time. The full
contract, including the derivation order and every halt reason, is in
[phase-transitions.md](references/phase-transitions.md).

Exit 1 means the situation could not be read, with the reason on stderr. That
is a repair, not a halt.

Done when: one line was printed and its branch below is selected.

### Step 2 - Run exactly one phase branch

#### Phase 0 - Bootstrap

```bash
python3 <skill-dir>/scripts/init_loop.py <feature> --root <root> \
  --objective "<the user's words, verbatim>" [--respawn <provider>]
```

Exit 1 names the precondition that failed: not a git repository, missing
`tasks.md`, `validate_tasks.py` rejected the plan, or the config does not
parse. Exit 2 is a refusal: already bootstrapped, or the harness could not be
resolved. **Never guess the harness** - a wrong guess misroutes every dispatch.
A harness with no verified environment marker does not auto-detect and must be
named with `--respawn`; codex is currently one of those
([provider-discovery.md](references/provider-discovery.md)).

Then check the whole config once, so a bad stage is found now rather than four
hours in:

```bash
python3 <skill-dir>/scripts/resolve_stage.py --validate --root <root> --feature <feature>
```

Exit 2 lists every offending stage at once.

Done when: `loop.json` exists and every configured stage resolves.

#### Phase B - Execute one batch

The detect line names the batch and its exact task ids. Use those ids. Never
"the next few tasks".

1. **Resolve the executor.**
   ```bash
   python3 <skill-dir>/scripts/resolve_stage.py --stage implement --root <root> \
     --feature <feature> --prompt "<payload>" --evidence <file>
   ```
   `kind=agent` means dispatch through the harness' own sub-agent mechanism.
   `kind=command` means spawn that command line.
2. **Build the payload** per [executors.md](references/executors.md): the task
   definitions in full, the Test Coverage Matrix, the spec ACs they trace to,
   the gate commands, `coding-principles.md` from the sibling skill, the
   evidence path, and the "do not commit" rule stated verbatim.
3. **Verify the evidence**, then **re-run the gate yourself**. A reported gate
   result is a claim about a command; run the command.
4. **Checkpoint each task, in order.**
   ```bash
   python3 <skill-dir>/scripts/checkpoint.py <feature> --root <root> \
     --task T7 --gate quick --gate-result PASS --message "<conventional commit>"
   ```
   Exit 2 is a refusal: no asserted pass, or `check_commit.py` rejected the
   message. A task that legitimately produced no diff is committed empty and
   the line ends `PASS empty`; nothing else has to be recorded, because the
   trailers are in git.
5. **Record a `reconciled=<ids>` field if the detect line carried one.** It
   means `tasks.md` ticks those tasks as done and git does not confirm it. Git
   already decided - they are in the batch and you run them - but the override
   is recorded, not swallowed:
   ```bash
   python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> --reconciled T4,T5
   ```
   Recording is keyed by task id, so repeating it costs nothing.
6. **Close the iteration.**
   ```bash
   python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> \
     --iteration-done --phase B --action "executed P1+P2" \
     --batch "T1,T2,T3" --commit <sha>
   ```
   `--commit` resets the no-progress counter. Omitting it increments the
   counter, which is how a loop that stops producing commits eventually halts.

A worker that fails a task reports it and stops. The next batch does not start
until that failure is resolved.

Done when: every task in the batch carries a `Task:` trailer.

#### Phase V - Verify

1. Resolve `--stage verify`. It must be a **fresh executor that did not author
   the code**. An author re-checking its own work reapplies the blind spot that
   produced the gap.
2. It runs **read-only over the real tree**. Its discrimination sensor mutates
   only a scratch copy, which is discarded. It does not fix.
3. It writes `.specs/features/<feature>/validation.md`: verdict, per-AC
   evidence with `file:line` citations, sensor result, diff range.
4. Record the verdict:
   ```bash
   python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> \
     --verify-round FAIL --gaps 2 --report .specs/features/<feature>/validation.md \
     --iteration-done --phase V --action "verify round 1"
   ```
5. On FAIL, distil the grounded failures into lessons with the sibling's
   `lessons.py`. A clean PASS records nothing.
6. `verify.max_rounds` is enforced by the detector, not by you. Once the rounds
   are spent without a PASS, the next detect prints
   `phase=H action=halt reason=verify_exhausted` in place of another round.
   Record the verdict as above and re-enter detection; do not start a round the
   detect line did not name.

Done when: a verdict is recorded. PASS moves toward `E`; FAIL with open gaps
moves to `F`.

#### Phase F - Fix

1. Resolve `--stage fix`. It is a **different executor from the verifier**,
   which is the whole reason fix is its own phase instead of a step inside
   verify.
2. Hand it the ranked gaps from `validation.md` verbatim, plus the ACs they
   violate, so the fix targets the requirement and not the symptom.
3. Checkpoint the fixes exactly as in phase B. The fix implementer does not
   commit and does not declare itself verified.
4. Close the round:
   ```bash
   python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> \
     --gaps 0 --iteration-done --phase F --action "consumed 2 gaps"
   ```
   Gaps back to zero returns detection to `V` for a fresh round.

Done when: `gaps_open` is 0 and the fixes are committed.

#### Phase E - Done

Detection prints `phase=E` only after `validate_state.py` exits 0, so the
verdict is already deterministic by the time this branch runs.

1. Walk the Phase E section of [checklist.md](references/checklist.md).
2. Record completion:
   ```bash
   python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> \
     --status complete --iteration-done --phase E --action "done"
   ```
3. Print the iteration summary with `phase_out = E`.
4. Print the done-signature **as the final line**:
   ```
   __TLC_LOOP__ feature=<feature> verify=PASS
   ```
5. Stop. `E` is the only successful terminal.

Done when: the checklist passes, the summary is printed, and the signature is
the last line of output.

#### Phase H - Halt

The line carries `reason` and `detail`. Implemented reasons: `no_progress`,
`gate_stuck`, `executor`, `limit`, `blocker`, `blast_radius`, `state_corrupt`,
`verify_exhausted`.

The last two are derived by `detect_phase.py` on the spot rather than read back
out of `loop.json`: a state file that cannot be parsed cannot record why, and
the verify ceiling is a comparison against the config, not a stored flag. This
list is kept in step with `update_loop.HALT_REASONS` by a test, not by memory -
it drifted once already.

1. Print the iteration summary with the halt reason filled in.
2. **Do not print the done-signature.** It means verified; a halted run is not.
3. Stop. A halt does not clear itself: re-invoking without changing the cause
   prints the same line. A human resolves the cause, or the config that tripped
   a limit changes.

A proven external blocker is the one halt that also sets `--status blocked`.
All three criteria in [recovery-loop.md](references/recovery-loop.md) must
hold, with evidence of exhausted alternatives.

Done when: the reason is recorded and the run has stopped.

### Step 3 - Self-audit, summarize, continue

1. Walk [checklist.md](references/checklist.md) for the phase just executed.
   Every box must pass.
2. Print the block from
   [iteration-summary.template.md](assets/iteration-summary.template.md).
3. **Continue gate: re-enter Step 1 immediately, in the same turn.** Stop only
   when the line just handled was `phase=E` or `phase=H`. The summary marks the
   round; it does not end the turn. `continue.in_turn = false` disables this and
   returns control after each iteration.

---

## Continuation across turns

The continue gate covers one turn. When the turn itself ends, `continue.mode`
decides what restarts it:

| `mode` | Mechanism |
| --- | --- |
| `auto` | Resolved from the harness recorded at bootstrap. |
| `goal` | Claude Code `/goal`, or the codex native goal. Both judge the transcript. |
| `shell` | `bash <skill-dir>/scripts/loop.sh <feature> --root <root>` |
| `none` | Nothing restarts the turn; the run continues when the user re-invokes. |

A goal evaluator reads the conversation. It does not run commands and does not
read files, which is exactly why the done-signature exists: the script decides,
the loop prints the decision, the evaluator matches the printed line. Ready-made
condition text: [goal-condition.template.md](assets/goal-condition.template.md).

`loop.sh` breaks on `phase=E` (exit 0) and `phase=H` (exit 1), and on anything
it cannot act on (exit 2). It never retries: the counters that would eventually
halt a run live in `loop.json`, and only the agent writes them.

---

## References

| File | Contents |
| --- | --- |
| [phase-transitions.md](references/phase-transitions.md) | The `detect_phase.py` contract: vocabulary, derivation order, exit rules |
| [recovery-loop.md](references/recovery-loop.md) | Repair procedure, failure classifications, external-blocker test |
| [executors.md](references/executors.md) | Payload format, evidence contract, the two universal executor rules |
| [providers.md](references/providers.md) | Adapter table per provider |
| [provider-discovery.md](references/provider-discovery.md) | How each marker and effort value was obtained, and which are unresolved |
| [state-schema.md](references/state-schema.md) | `loop.json` fields and invariants |
| [config-schema.md](references/config-schema.md) | `loop.config.toml` keys and defaults |
| [checklist.md](references/checklist.md) | Per-iteration self-audit |
| [goal-condition.template.md](assets/goal-condition.template.md) | Ready-made `/goal` condition |
| [iteration-summary.template.md](assets/iteration-summary.template.md) | The summary block printed each iteration |
| [loop.config.example.toml](assets/loop.config.example.toml) | Commented starter config |
