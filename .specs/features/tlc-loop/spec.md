# tlc-loop Specification

## Problem Statement

`tlc-spec-driven` is invoked phase by phase: the agent runs Execute, stops at the
end of its turn, and waits for the user to prompt the next step. For a feature
with twenty tasks that means the user must actively drive every batch, and any
command failure ends the run instead of being repaired. `cy-loop-tasks` solves
exactly this in the Compozy ecosystem, but it is welded to that stack (`herdr`
workers, `cy-*` skills, `make gate`, `.compozy/tasks/`). This feature ports the
transferable half — deterministic phase detection, a self-healing repair loop,
atomic checkpoints, and unattended continuation — into a stack-agnostic sibling
skill, and adds per-stage model/effort configuration so a long run can pair a
cheap implementer with a high-reasoning verifier.

## Goals

- [ ] A feature with a formal `tasks.md` runs from first task to verified PASS without per-batch prompting
- [ ] Any interrupted run resumes to the correct next action from filesystem and git evidence alone
- [ ] Command, gate, and executor failures are repaired inside the current phase instead of ending the run
- [ ] Each stage (`implement`, `verify`, `fix`) runs on a provider, model, and effort chosen by configuration
- [ ] The loop never depends on a single agent harness — Claude Code, codex, and a plain shell all drive it

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| --- | --- |
| Specify, Design, and Tasks phases | Human review pays off most on hard-to-reverse decisions; the loop starts at an approved `tasks.md` |
| QA phase (Phase C of `cy-loop-tasks`) | Depends on Compozy-only `qa-report` / `qa-execution` skills; the Verifier already gates quality |
| `herdr` as a required dependency | Replaced by the generic executor abstraction; `herdr` remains usable as one `command` executor |
| Stacked PRs (`gh stack`, `--stacked`) | Publishing layers is remote-facing work outside the local-commit blast radius |
| Token accounting implemented by this skill | Neither Claude Code nor a shell script exposes it reliably; harness-native counters are read opportunistically |
| Modifying `tlc-spec-driven` beyond one handoff hook | The sibling skill drives it; rewriting it would fork the ecosystem |
| Rewriting `.specs/loop.config.toml` from the loop | Config is user-owned and read-only to the loop; runtime resolution belongs in `loop.json` |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Task completion has no status field in `tlc-spec-driven` | Record completion as git trailers `Task: TN` and `Gate: <level> PASS` on the atomic commit | `tasks.md` checkboxes sit under "Done when" and are acceptance criteria, not task state; `validate_tasks.py` never parses status. Verified: `git commit --trailer` writes, `%(trailers:key=Task,valueonly)` reads, `check_commit.py` exits 0 | y |
| Dispatch granularity for Phase B | Batches of ~7 tasks (whole phases) with one atomic commit per task inside the worker | Batching solves context budget, the trailer solves recovery granularity; with git as truth the two no longer trade off | y |
| Verifier may remediate its own findings | No - Verifier stays read-only, a separate `fix` stage consumes the ranked gaps | `cy-loop-tasks` collapses them; `tlc-spec-driven` keeps author != verifier as its quality gate | y |
| Ceiling on verify rounds | Configurable, no hard-coded maximum | Explicit user decision; the runaway detectors and global breaker cover the risk instead | y |
| Model and effort expressed uniformly across providers | No - a per-provider adapter table translates `provider`/`model`/`effort` into a command line | Verified: `codex` uses `-m` plus `-c model_reasoning_effort=`, `cursor-agent` bakes effort into the model name or bracket syntax, Claude Code takes both as separate fields | y |
| Valid `effort` values | `low`, `medium`, `high`, `xhigh`, `max` | `ultra` exists in no installed provider; the adapter rejects values the target provider does not accept | y |
| Which harness drives continuation | Resolved at runtime: `/goal` on Claude Code, native goals on codex, `loop.sh` elsewhere | `/goal` starts the next turn when the previous finishes and is judged by a fresh model; `/loop` is interval-based and unsuitable as the motor | y |
| The goal evaluator can run scripts | No - it only reads the conversation, so the loop prints a literal done-signature line after `validate_state.py` exits 0 | Documented behaviour of `/goal`; this is why `cy-loop-tasks` carries a done-signature at all | y |
| Detecting the running harness | `respawn.provider: auto` reads environment markers at bootstrap and records the result in `loop.json`; a dedicated discovery task probes `codex` and `cursor-agent` and records their real markers before `auto` is implemented | Verified for Claude Code (`CLAUDECODE=1`); the other two are unverified, so the discovery task resolves them and failed detection halts and asks rather than guessing | y |
| Where the project keeps loop state | `.specs/features/<feature>/loop.json`, machine-owned, single writer | Mirrors the `state.yaml` invariant of `cy-loop-tasks`; YAML fails loudly on corruption where Markdown fails silently | y |

**Open questions:** none - all resolved or logged above (required before the spec is confirmed).

---

## User Stories

### P1: Deterministic phase detection and resume ⭐ MVP

**User Story**: As a developer running a long feature, I want the loop to derive
the next action from durable evidence, so that an interrupted session resumes
exactly where it stopped instead of redoing finished work.

**Why P1**: Every other capability depends on knowing what to do next. Without
it, restart is guesswork and unattended execution is impossible.

**Acceptance Criteria**:

1. WHEN the loop is invoked for a feature THEN the system SHALL print exactly one phase line describing the next action before performing any work
2. WHEN deriving completed tasks THEN the system SHALL read git trailers via `git log --format="%(trailers:key=Task,valueonly)"` and treat that result as authoritative over `loop.json`
3. IF `loop.json` is absent THEN the system SHALL reconstruct the phase from git history and `tasks.md` rather than failing the run
4. IF `loop.json` exists but is unparseable THEN the system SHALL halt with `phase=H reason=state_corrupt` rather than reconstructing, because reconstruction would silently discard the immutable objective
5. IF `tasks.md` and git history disagree about a task THEN the system SHALL treat git as the source of truth and record the reconciliation in `loop.json`
6. The system SHALL mutate `loop.json` only through its own state-writing script, never by hand-editing or by another writer

**Independent Test**: Delete `loop.json` mid-feature, re-invoke the loop, and confirm it names the same next task that git history implies.

---

### P1: Atomic checkpoint per task ⭐ MVP

**User Story**: As a developer reviewing an unattended run, I want each task to
land as one atomic commit carrying its own verification record, so that history
is bisectable and no task is silently half-done.

**Why P1**: The checkpoint is what makes a crash cost one task instead of the
whole run, and it is the mechanism that records status.

**Acceptance Criteria**:

1. WHEN a task's gate check passes THEN the system SHALL create one atomic commit containing the implementation, its tests, and the trailers `Task: <id>` and `Gate: <level> PASS`
2. IF the gate check has not passed THEN the system SHALL NOT create the commit for that task
3. WHEN composing the commit message THEN the system SHALL validate it with `check_commit.py` and SHALL abort the commit on a non-zero exit
4. The system SHALL create at most one commit per task and SHALL never batch multiple tasks into a single commit
5. WHERE an executor other than the orchestrator performed the work, the system SHALL forbid that executor from committing and SHALL create the checkpoint itself
6. IF a task produces no file changes THEN the system SHALL record its completion without fabricating a source diff

**Independent Test**: Run a two-task feature and confirm `git log` shows two commits, each with a `Task:` trailer, and `check_commit.py` passes on both messages.

---

### P1: Self-healing repair loop ⭐ MVP

**User Story**: As a developer who is not watching the run, I want failures to be
diagnosed and repaired inside the current phase, so that a formatter error at 2am
does not end an eight-hour run.

**Why P1**: Without repair, unattended execution fails on the first transient
problem, and the loop is no better than manual invocation.

**Acceptance Criteria**:

1. WHEN a command, gate, or executor check fails THEN the system SHALL keep the current phase action open and SHALL NOT write final iteration state
2. WHEN repairing a failure THEN the system SHALL diagnose the root cause before retrying, and SHALL NOT retry an unchanged command as its only remedy
3. The system SHALL NOT weaken an assertion, delete a test, or skip a test case in order to make a gate pass
4. IF a failure is repairable THEN the system SHALL repair it and continue rather than reporting a blocker
5. IF all three external-blocker criteria hold THEN the system SHALL record the evidence and exhausted alternatives, halt, and SHALL NOT print the done-signature

**Independent Test**: Introduce a lint error outside the task's files, run the loop, and confirm it repairs and continues instead of halting.

---

### P1: Independent verification with bounded fix loop ⭐ MVP

**User Story**: As a developer trusting an unattended result, I want completion
judged by an agent that did not write the code, so that the verdict is not the
author re-applying its own blind spots.

**Why P1**: `tlc-spec-driven` makes the Verifier always-on and never prompted. A
loop that skips it violates the parent skill's execution contract, so it is not
optional at any priority.

**Acceptance Criteria**:

1. WHEN the final task of a feature is committed THEN the system SHALL dispatch a fresh verifier that did not author the code, without prompting the user
2. WHILE the verifier is running, the system SHALL keep it read-only and SHALL NOT let it modify code or tests in the real working tree
3. WHEN the verifier returns FAIL THEN the system SHALL route the ranked gaps to a separate `fix` stage and SHALL re-dispatch the verifier afterwards
4. IF the configured verify-round limit is reached without PASS THEN the system SHALL halt and escalate to the user
5. WHEN the verifier reports PASS THEN the system SHALL confirm it with `validate_state.py` and SHALL treat a non-zero exit as not done

**Independent Test**: Force a spec gap, run to completion, and confirm the verifier reports FAIL, a fix round runs, and the second verification is performed by a fresh agent.

---

### P1: Per-stage provider, model, and effort ⭐ MVP

**User Story**: As a developer managing token budget across vendors, I want each
stage to run on a provider and reasoning tier I choose, so that a cheap
implementer can be paired with a high-reasoning verifier.

**Why P1**: Pairing a cheap implementer with a high-reasoning verifier is the
stated reason this feature exists. A v1 without it runs, but does not deliver the
capability that justifies building the loop.

**Acceptance Criteria**:

1. WHEN dispatching a stage THEN the system SHALL resolve `provider`, `model`, and `effort` from `.specs/loop.config.toml` and SHALL translate them through the provider adapter table
2. IF a configured `effort` value is not supported by the target provider THEN the system SHALL reject the configuration before dispatch instead of sending it and failing silently
3. WHERE the configured provider equals the running orchestrator, the system SHALL use the harness-native sub-agent mechanism instead of spawning a CLI
4. The system SHALL treat `.specs/loop.config.toml` as read-only and SHALL record runtime-resolved values in `loop.json` instead
5. WHEN an executor reports a launch, authentication, or quota failure THEN the system SHALL halt with that reason recorded so the provider can be changed and the run resumed
6. The system SHALL verify an executor's reported evidence exists before advancing state, and SHALL NOT accept a completion claim without it

**Independent Test**: Configure `implement` on one provider and `verify` on another, run a small feature, and confirm each stage was dispatched to the configured CLI with the translated flags.

---

### P1: Unattended continuation and stop conditions ⭐ MVP

**User Story**: As a developer starting a long run before stepping away, I want
the loop to keep going across turns and stop for a clear reason, so that I return
to either a finished feature or an explained halt.

**Why P1**: Without it the loop still stops at every turn boundary, which is the
exact problem the feature exists to remove. Safe only once detection,
checkpoints, and repair are in place, so it is sequenced after them.

**Acceptance Criteria**:

1. WHILE the phase is not terminal and no stop condition holds, the system SHALL re-enter detection in the same turn instead of returning control to the user
2. WHEN `validate_state.py` exits 0 THEN the system SHALL print the literal done-signature line so an external evaluator can observe completion from the transcript
3. WHEN no continuation mode is configured explicitly THEN the system SHALL resolve one from the running harness and SHALL record the resolved value in `loop.json`
4. IF harness detection is inconclusive THEN the system SHALL halt and ask rather than guessing a continuation mechanism
5. WHEN the bootstrap records the run's objective THEN the system SHALL keep it immutable for the remainder of the run
6. IF no new commit appears across the configured number of iterations THEN the system SHALL halt and report lack of progress
7. IF the same task's gate fails more than the configured number of attempts THEN the system SHALL halt rather than continue repairing
8. IF a configured `max_iterations` or `max_minutes` limit is reached THEN the system SHALL write state and halt cleanly so the run can be resumed
9. WHEN a push, deploy, or other remote or destructive operation is required THEN the system SHALL halt and wait for explicit authorization instead of proceeding

**Independent Test**: Start a run with a low `max_iterations`, confirm it halts cleanly at the limit, and confirm re-invoking resumes from the recorded state.

---

### P2: Handoff from tlc-spec-driven

**User Story**: As a developer finishing the Tasks phase, I want the loop offered
at the moment it is relevant, so that I do not have to remember it exists.

**Why P2**: Convenience, and the only story that edits another skill. Manual
invocation already works, so it is sequenced last.

**Acceptance Criteria**:

1. WHEN Execute begins with a formal `tasks.md` that exceeds one batch THEN the system SHALL present loop mode alongside the existing inline and sub-agent options
2. IF the user does not choose loop mode THEN the system SHALL fall back to the existing `tlc-spec-driven` behaviour unchanged

**Independent Test**: Approve a 20-task `tasks.md` and confirm the delegation offer lists three options rather than two.

---

## Edge Cases

- IF the project is not a git repository THEN the system SHALL halt at bootstrap with that reason, since task status derives from commit trailers
- IF `tasks.md` is missing or fails `validate_tasks.py` THEN the system SHALL refuse to start the loop and SHALL report the validation errors
- IF a commit is amended or rebased such that a `Task:` trailer is duplicated THEN the system SHALL treat the task as completed once and SHALL record the ambiguity
- IF the working tree contains uncommitted changes that map to no current task THEN the system SHALL halt and ask rather than committing or discarding them
- IF an executor commits despite the prohibition THEN the system SHALL keep the phase open, preserve that work, and SHALL NOT advance state
- WHEN a batch worker reports a task failure THEN the system SHALL NOT start the next batch until the failure is resolved
- IF `.specs/loop.config.toml` is absent THEN the system SHALL run on documented defaults rather than failing
- IF the configured provider CLI is not installed THEN the system SHALL halt with the missing command named

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| LOOP-01 | P1: Deterministic phase detection and resume | Execute | Verified |
| LOOP-02 | P1: Atomic checkpoint per task | Execute | Verified |
| LOOP-03 | P1: Self-healing repair loop | Execute | Verified |
| LOOP-04 | P1: Independent verification with bounded fix loop | Execute | Verified |
| LOOP-05 | P1: Per-stage provider, model, and effort | Execute | Verified |
| LOOP-06 | P1: Unattended continuation and stop conditions | Execute | Verified |
| LOOP-07 | P2: Handoff from tlc-spec-driven | Tasks | Not delivered (T26 awaiting go-ahead) |
