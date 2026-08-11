# Self-healing recovery loop

Read this file in full the moment any of these happens:

- a gate command exits non-zero,
- `checkpoint.py`, `update_loop.py`, `init_loop.py`, or `resolve_stage.py`
  exits non-zero,
- a promised evidence artifact is absent or empty,
- an executor reports a failure, times out, or breaks one of the two rules in
  [executors.md](executors.md).

**A failure is repairable by default.** It stays inside the current phase
action: no iteration is closed, no checkpoint is made, no counter moves. The
loop advances on evidence, and a failure is evidence that the phase is not
finished yet.

**One counter is the exception: a failed gate.** Phase B records it with
`update_loop.py --gate-attempt <TN>` on the failing attempt, before the repair
below starts. It is what `limits.gate_attempts_per_task` bounds, so leaving it
unwritten does not keep the run clean - it removes the only thing that stops a
wrong diagnosis from being repaired forever.

`status = blocked` is reserved for an external blocker proven by the
three-criteria test at the bottom of this file. Nothing else earns it.

---

## Repair loop

1. **Capture.** Record the exact command, its exit status, the decisive lines
   of output, and every file the output names. Change nothing yet. `loop.json`
   stays untouched: an intermediate failure never calls `update_loop.py`, with
   the single exception named above - a failed gate is recorded with
   `--gate-attempt <TN>` before this step, because the attempt is what the
   limit counts.
2. **Diagnose the root cause.** Read the failing tool's own message and the
   project's instructions before editing anything. When the output names a safe,
   in-scope repair command, run it rather than describing it.
3. **Apply the root-cause repair.** Fix the thing that is wrong, not the symptom
   the gate happened to surface. Inspect every resulting diff and preserve
   changes you did not intend to make.
4. **Re-run the narrowest command that reproduces the failure.**
   **A blind rerun is not a repair.** A flake, a timeout, a race, or an
   intermittent executor needs a diagnosis or a changed precondition first.
   Re-running an unchanged command and getting a different answer teaches you
   nothing about which run was the lie.
5. **Re-run the task's full gate level** from the Gate Check Commands table in
   the feature's `tasks.md`. Fixing one lane can invalidate another. A new
   failure restarts at step 1, still inside the same phase action.
6. **Only now close the iteration.** Call `update_loop.py` once, print the
   iteration summary, and continue.

Done when every failure observed in this phase action is repaired, the required
artifacts exist, and the phase's gate is green.

---

## What a repair may never be

These are not shortcuts, they are the failure. The gate is the only thing
standing between an unattended run and a repository full of green lies.

- **Never weaken an assertion** to make it pass more easily.
- **Never delete a test** to reduce the failure count.
- **Never skip, disable, or mark a test pending** to get past it.
- **Never edit a test so it matches the implementation.** Tests derive from the
  spec. If a test is genuinely wrong about the spec, that is a stop-and-ask,
  not a repair.
- **Never bypass a hook.** No `--no-verify`, no `--no-gpg-sign` as a workaround,
  no `git commit` outside `checkpoint.py`.
- **Never rewrite history** to hide a bad commit. Record the ambiguity instead.

A repair that touches a test file is legitimate only when the test itself is
the thing that broke (a leaked temp directory, an order dependence, a hardcoded
clock). Say which in the iteration summary.

---

## Normative classifications

Gate levels are the parent skill's: `quick`, `full`, `build`. The concrete
command for each lives in the feature's own Gate Check Commands table, so this
table names the level, never a specific build tool.

| Failure | Required autonomous action |
| --- | --- |
| A test fails under `quick` or `full` | Diagnose the production code or the contract it violates, fix that, re-run the narrow lane, then re-run the level. |
| A test passes alone and fails in the suite | Order dependence or leaked state. Find the shared resource, isolate it, re-run the whole level. Never reorder the suite to hide it. |
| A test is intermittent | Reproduce under bounded conditions and fix the cause. Raising a timeout or adding a sleep is not a fix. |
| The `build` level fails on syntax, compile, or lint | Fix the source it names, then re-run the whole level. |
| A required tool or dependency is missing locally | Use the project's own documented install or bootstrap command when it is safe and deterministic, then resume. Not a blocker. |
| `checkpoint.py` exits 2 - message rejected by `check_commit.py` | Rewrite the message to Conventional Commits and retry. The message is wrong, not the validator. |
| `checkpoint.py` exits 2 - trailer contradicts the flags | The message and the flags disagree about the task or gate level. Decide which is right, correct it, retry. |
| `checkpoint.py` exits 1 - git or a hook refused the commit | Repair the hook's complaint at its root and retry the normal checkpoint. If the repair changed tracked source, re-run the gate first. |
| `checkpoint.py` prints a SHA ending `PASS empty` | Not a failure, and nothing else has to be recorded. See the no-diff contract in [state-schema.md](state-schema.md#the-no-diff-contract). |
| An evidence artifact is missing or empty | Keep the phase open. Re-collect the evidence or re-run the lane. A completion claim without its artifact is not completion. |
| An executor committed despite the ban | Keep the phase open, preserve the commit, run the gate yourself, repair trailer ownership, record the ambiguity. Never discard the work. |
| A sibling-skill script cannot be resolved | `_paths` prints the absolute path it tried. Repair the installation so `tlc-spec-driven` sits next to this skill, then resume. |
| `detect_phase.py` exits 1 - `loop.json` unparseable | Diagnose the interrupted or malformed write from the parse error on stderr. **Do not delete `loop.json` to make the error go away**: it holds the immutable objective, and deleting it silently redefines the run's success criterion. |
| `detect_phase.py` exits 1 - `tasks.md` missing, or not a git repository | Environment repair. Restore the file or run from the right root; neither is a blocker. |
| `resolve_stage.py` exits 2 - unknown provider, unsupported effort, unfilled placeholder | The loop cannot repair this: `loop.config.toml` is user-owned and read-only to the loop. Halt with `phase=H reason=executor` and the resolver's message as detail, so the user edits the config and resumes. |
| An executor CLI is missing, unauthenticated, or out of quota | Halt with `phase=H reason=executor`, naming the command. No amount of retrying renews a token. |
| An executor exceeds `limits.executor_timeout_seconds` | Kill it, keep the partial output for diagnosis, halt with `phase=H reason=executor`. A timeout is an executor failure, not a retry condition. |
| The same task's gate keeps failing past `limits.gate_attempts_per_task` | Nothing to record by hand: each failed attempt already moved `--gate-attempt`, so detection derives `phase=H reason=gate_stuck` and names the task itself. Repeated repair on one task is a signal that the diagnosis is wrong. |
| Uncommitted changes map to no current task | Halt with `phase=H reason=blocker`. Never commit them into someone else's task, and never discard them. |
| A push, deploy, migration, or other remote or destructive step is required | Halt with `phase=H reason=blast_radius` and wait. See below. |

---

## Blast radius halts, it does not ask

Approving a spec and a `tasks.md` authorizes local implementation and local
commits. Nothing else.

When the work needs `git push`, a force-push, a deploy, a production data
change, or any other remote or externally visible operation, the loop **halts
and waits**:

```bash
python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> \
  --halt blast_radius --detail "<the exact operation that needs authorization>"
```

**Halting is not asking.** An unattended run has nobody to answer a prompt, so
a question and a hang are the same event. Recording the halt leaves the run
resumable the moment a human reads the reason; a prompt leaves a process
sitting on a pipe until someone kills it.

The same logic is why the loop passes every built-in `command` executor its own
approval bypass - `--dangerously-skip-permissions`,
`--dangerously-bypass-approvals-and-sandbox`, `--force` - rather than leaving it
to the operator's configuration. A dispatched executor therefore runs with no
approval guardrail at all, by design; the only safe place to stop is at the
phase boundary, in the phase vocabulary. The blast radius that buys is spelled
out in [providers.md](providers.md).

---

## External-blocker test

Stop and record `blocked` only when **all three** are true.

1. **The phase cannot reach its completion criterion without one specific
   missing external input**: a credential, an authorization, an approval for a
   blast-radius operation, a product decision only the user can make, an
   external service, or unavailable infrastructure.
2. **Every safe in-scope alternative has been attempted and recorded with
   evidence.** Named commands, their exit codes, and what each produced.
3. **The missing input cannot be derived from repository truth**, and the loop
   cannot create, repair, restart, regenerate, or replace it within the
   authority it already has.

### What does not qualify

None of these is a blocker, however long it has been going on:

| Not a blocker | Because |
| --- | --- |
| A failing gate | That is the repair loop's entire job. |
| A flaky or slow test | Diagnosable. Fix the cause. |
| A large or complex diff | Difficulty is not a missing input. |
| A dirty worktree | Either the changes belong to a task, or they are the `blocker` halt above, decided by evidence. |
| Repeated repair attempts | Attempts are not evidence of impossibility; the `gate_stuck` limit is what bounds them. |
| Elapsed time | The `limit` halt is what bounds a run, and it is a clean stop, not a blocker. |
| A missing local tool with a documented install command | Install it. |
| A rejected commit message | Rewrite it. |
| The implementation disagreeing with the spec | Add a `SPEC_DEVIATION` marker and report it. A gap in the spec is a finding, not a wall. |
| An idea for something better | Out of scope by definition. Record it and move on. |

### Recording a proven blocker

```bash
python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> \
  --halt blocker \
  --detail "<the missing input, and the alternatives already exhausted>" \
  --status blocked
```

`--halt` alone records `status = halted`; adding `--status blocked` is what
distinguishes a proven external blocker from an ordinary stop, and it is
applied last so it wins.

Then print the iteration summary with the halt reason, and **do not print the
done-signature**. The signature means the feature is verified. A blocked run
has not been.
