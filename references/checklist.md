# Per-iteration self-audit

Walk this before printing the iteration summary. A failing box means the
iteration is **not** finished: do the missing work and re-check. Never print
the done-signature with an open box.

**Every item is checkable against an artifact or a command's output.** Nothing
here is answered from memory. If a box can only be confirmed by recalling what
happened, it is the wrong box: find the file or the exit code that proves it.

---

## Every iteration

- [ ] `detect_phase.py` was the first action of the iteration, and the branch
      that ran matches the `phase=` in its printed line.
      *Evidence: the line in the transcript.*
- [ ] Exactly one phase action ran. No branch was started "while we are here".
      *Evidence: the transcript shows one branch between two detect lines.*
- [ ] Every non-zero exit ran the repair loop in
      [recovery-loop.md](recovery-loop.md), and no intermediate failure closed
      an iteration or printed a summary.
      *Evidence: no `update_loop.py --iteration-done` call sits between a
      failure and its repair.*
- [ ] `loop.json` changed only through `update_loop.py`.
      *Evidence: `git diff -- .specs/features/<feature>/loop.json` matches what
      the recorded flags would produce; no hand edit.*
- [ ] The iteration was closed exactly once.
      *Evidence: one `updated feature=… iteration=N` line, with `N` one higher
      than the previous iteration.*
- [ ] The summary block was printed from
      [iteration-summary.template.md](../assets/iteration-summary.template.md)
      with every placeholder filled.
- [ ] **Continue gate.** If the handled line was not `phase=E` or `phase=H`,
      Step 1 was re-entered in the same turn.
      *Evidence: the next detect line follows the summary in the transcript.*

## Phase 0 - bootstrap

- [ ] `init_loop.py` exited 0.
      *Evidence: its `bootstrapped feature=… harness=… (…)` line.*
- [ ] The harness was detected from a verified marker or named with
      `--respawn`. It was never guessed.
      *Evidence: the reason in parentheses on that same line.*
- [ ] `objective` in `loop.json` is the user's text verbatim, not a paraphrase
      or a derived restatement.
      *Evidence: diff the field against the invocation text.*
- [ ] `resolve_stage.py --validate` exited 0, so no stage is unusable.
      *Evidence: its `ok N stage(s) resolve` line.*
- [ ] No `update_loop.py` call was made. Bootstrap writes state exactly once,
      through `init_loop.py`, and the next detect re-derives from git.

## Phase B - execute one batch

- [ ] The tasks executed are exactly the ids in the detect line: none added,
      none dropped.
      *Evidence: compare the `tasks=` list against the checkpoint calls.*
- [ ] The payload stated "do not commit" verbatim, per
      [executors.md](executors.md).
      *Evidence: the dispatched payload text.*
- [ ] Every dispatched lane's evidence artifact exists and is non-empty.
      *Evidence: the file at the `--evidence` path.*
- [ ] The gate was re-run by the orchestrator. The exit code used is its own,
      not the executor's claim.
      *Evidence: the gate command and its exit code in the transcript.*
- [ ] One `checkpoint.py` call per task, each printing a short SHA or
      `SKIP: no changes`.
- [ ] Every `SKIP: no changes` has a matching
      `update_loop.py --task-done TN --no-diff`, or detection will re-dispatch
      that task forever.
      *Evidence: `no_diff_tasks` in `loop.json`.*
- [ ] `git log --format="%(trailers:key=Task,valueonly)"` now lists every task
      in the batch.
- [ ] HEAD moved only through `checkpoint.py`. No executor commit.
      *Evidence: every commit since the batch started carries a `Task:` trailer
      and a Conventional Commits header.*

## Phase V - verify

- [ ] **The verifier is a fresh executor that did not author the code.** An
      author re-checking its own work reapplies the blind spot that produced
      the gap, so a shared executor voids the round.
      *Evidence: the resolved `--stage verify` invocation, and that it is not
      the process that ran `--stage implement` or `--stage fix`.*
- [ ] The verifier ran read-only over the real tree.
      *Evidence: `git status --porcelain` before and after differ only by
      `validation.md`; the sensor's scratch copy is gone.*
- [ ] `validation.md` exists and carries all four parts: a verdict, per-AC
      evidence with `file:line` citations, the sensor result, and the diff
      range.
- [ ] The verdict recorded with `--verify-round` is the verdict written in
      `validation.md`.
      *Evidence: `verify.last_verdict` in `loop.json` against the report.*
- [ ] `verify.gaps_open` matches the number of ranked gaps in the report.
- [ ] On FAIL, the grounded failures were distilled into lessons through the
      sibling skill's `lessons.py`. A clean PASS records nothing.
- [ ] If `verify.max_rounds` is spent without a PASS, no further round was
      started. The detector enforces this: it prints
      `phase=H action=halt reason=verify_exhausted` instead of `phase=V` or
      `phase=F`, so nothing has to be recorded by hand.
      *Evidence: the detect line, against `verify.rounds` in `loop.json` and
      `verify.max_rounds` in `loop.config.toml`. An omitted `max_rounds` is
      unlimited, so no halt is due.*

## Phase F - fix

- [ ] The fix executor is not the verifier that produced the gaps. That
      separation is why fix is its own phase.
      *Evidence: the resolved `--stage fix` invocation.*
- [ ] Every ranked gap in `validation.md` was addressed, or deferred with a
      written reason.
      *Evidence: gap list against the diff.*
- [ ] No assertion was weakened, no test deleted, no test skipped.
      *Evidence: the test count before and after the fix; the diff of the test
      files.*
- [ ] The fixes were committed by `checkpoint.py`, not by the executor.
- [ ] `--gaps 0` was recorded, which returns detection to `V`.
      *Evidence: `verify.gaps_open` is 0 in `loop.json`.*

## Phase E - done

- [ ] Detection printed `phase=E`, which means `validate_state.py` exited 0.
      *Evidence: re-run it if there is any doubt; exit 0 is the only success.*
- [ ] The `validation.md` verdict is PASS and cites `file:line` evidence, not
      prose.
- [ ] `pending` is genuinely empty: every task in `tasks.md` carries a `Task:`
      trailer or sits in `no_diff_tasks`.
      *Evidence: the trailer list against the parsed plan.*
- [ ] `--status complete` was recorded.
      *Evidence: `status` in `loop.json`.*
- [ ] The done-signature is the **last** line of output and carries this
      feature's name: `__TLC_LOOP__ feature=<feature> verify=PASS`.

## Phase H - halt

- [ ] The reason and detail come from the detect line, not from judgment.
      *Evidence: the printed `reason=` and `detail=` against the summary.*
- [ ] The summary block carries that reason, and **the done-signature was not
      printed**. It means verified; a halted run is not.
- [ ] Nothing was discarded. Work that triggered a `blocker` halt is still in
      the tree.
      *Evidence: `git status --porcelain` still shows it.*
- [ ] For `blast_radius`: no remote or destructive operation was attempted, and
      the run is waiting for explicit authorization rather than asking.
      *Evidence: no push, deploy, or migration command in the transcript.*
- [ ] For a `blocker` recorded with `--status blocked`: all three
      external-blocker criteria in [recovery-loop.md](recovery-loop.md) hold,
      and the exhausted alternatives are recorded with their exit codes.
- [ ] The run stopped. A halt does not clear itself, and re-invoking without
      changing the cause prints the same line.
