# Executor dispatch contract

An **executor** is whatever actually does a phase's work: a harness-native
sub-agent, or a CLI the loop spawns. `resolve_stage.py` decides which, using
the table in [providers.md](providers.md). This file specifies what the
executor is handed, what it must hand back, and what the loop does when it
does not.

The loop treats every executor identically, whichever provider it came from
and whichever role it is playing. There is no privileged executor and no
special case.

---

## The two universal rules

Both exist because an unattended run has nobody to notice when an executor is
wrong or lying.

### 1. An executor never commits

**The orchestrator creates every commit, through `checkpoint.py`. An executor
writes files and reports; it does not touch git history.** (LOOP-02 AC 5.)

Task status *is* the commit trailer. `detect_phase.py` derives what is done by
reading `Task:` trailers, and `checkpoint.py` writes one only after the caller
asserts a passing gate. An executor that commits on its own bypasses that
assertion, so a task could appear complete in the source of truth without any
gate ever having passed. The whole recovery model rests on a trailer meaning
"this task was verified", and an executor commit makes it mean "somebody
thought this was done".

It also breaks atomicity: one task, one commit, one gate record. An executor
committing mid-batch can merge two tasks into one commit or split one across
several, and neither is bisectable.

Say this explicitly in the payload. It is not inferable from the work.

**If an executor commits anyway**, do not discard the work and do not advance
state (spec.md edge case):

1. Keep the phase open. The task is not done for loop purposes.
2. Preserve the commit. It contains real work.
3. Repair ownership: run the gate yourself. If it passes, the commit can stand
   once its trailers are correct; if it does not, treat it as a failed task and
   repair.
4. Record the ambiguity. Never rewrite history to hide it.

### 2. Evidence is verified, never trusted

**A completion claim is not completion. Before state advances, the loop
confirms the artifact exists and says what the claim says** (LOOP-05 AC 6).

Executors report success they did not achieve. Not usually maliciously: a
truncated context, a timeout, or an optimistic summary all produce the same
"done" sentence. Prose in a final message is the one thing an executor can
always produce, so it is the one thing that cannot count as proof.

Two checks, in order:

1. **The evidence artifact exists and is non-empty**, at the path the loop
   named in `{evidence}`. Missing or empty means the executor did not finish,
   whatever it said.
2. **The gate is re-run by the orchestrator.** A reported gate result is a
   claim about a command; the loop runs that command itself, from the Gate
   Check Commands table, and uses its own exit code. This is what the
   orchestrator is asserting when it passes `--gate-result PASS` to
   `checkpoint.py`, so it must have grounds beyond the executor's word.

A claim without evidence does not fail the run. The phase stays open, the
evidence is re-collected, or the lane is re-run.

---

## A `command` executor is launched with no approval guardrail

Every built-in `command` executor is spawned with its approval prompts
disabled, by the loop itself, on every invocation:
`--dangerously-skip-permissions` for claude,
`--dangerously-bypass-approvals-and-sandbox` for codex, `--force` for cursor.
codex additionally runs unsandboxed.

This is deliberate and it is the price of unattended execution. Nobody is at
the keyboard, so an executor that stops to ask does not get an answer - it
hangs, produces nothing, and the run stalls until a human notices hours later.
That is the failure mode this skill exists to remove, so the prompt is removed
instead.

What it means in practice: a dispatched executor can write any file it can
reach and run any command, with no confirmation step. Its blast radius is the
machine it runs on. Point the loop at a repository and a machine where that is
acceptable.

The two rules above are what keep it bounded anyway - it never commits, and
nothing it says is believed without an artifact - and a genuinely dangerous
operation still **halts** rather than being auto-approved. The bypass buys
non-interactivity; it is not authorization. See
[providers.md](providers.md), "Blast radius".

A custom `[providers.<name>]` template gets no bypass from the loop, which has
no catalogue for it. Whoever writes the template supplies the flag.

---

## The payload

Every payload carries a common envelope, then the role-specific part.

### Common envelope

| Item | Why it is there |
| --- | --- |
| Feature name and repo path | Locates `.specs/features/<feature>/`. |
| The exact scope | Task ids, or the gap list. Never "continue where you left off". |
| Evidence path | The `{evidence}` file the executor must write. |
| **"Do not commit"** | Rule 1, stated verbatim. |
| Gate commands | From the Gate Check Commands table in `tasks.md`. |
| `coding-principles.md` | From the sibling skill. |
| Report format | What to put in the evidence file. |

The envelope never contains the loop's own state. An executor has no business
reading or writing `loop.json`.

### Batch worker

Runs one batch: one or more consecutive whole phases with one effective stage,
packed to the task budget. The `stage=` field on the Phase B detect line is
authoritative. Resolve that exact value with `resolve_stage.py`; never infer a
route from a phase title or silently substitute `implement`.

| Item | Detail |
| --- | --- |
| Task definitions | Every task in the batch, in full, in order. |
| Effective stage | The exact `stage=` value from the detect line. |
| Test Coverage Matrix | From `tasks.md`, so tests land in the right layer and location. |
| Spec ACs | The acceptance criteria the batch's tasks trace to. |
| Design context | Only the components the batch touches. |
| Per-task cycle | `implement.md`, **with the commit step removed**. |

The per-task cycle is the parent skill's, minus commits: implement, write tests
derived from the spec, run the gate, record the result, move to the next task.
The worker finishes every task in a phase before starting the next phase in its
batch. A stage transition is always a new batch, even when the task budget has
room.

**Reports per task:** task id, gate level, gate result, files changed, and any
`SPEC_DEVIATION`. Per task, not per batch: the orchestrator checkpoints one
task at a time and needs to know exactly which ones are safe to commit.

A worker that fails a task reports the failure and stops. The next batch does
not start until it is resolved (spec.md edge case).

### Verifier

Judges whether the feature meets its spec. Runs on a provider chosen for
reasoning quality, which is usually not the implementer's.

| Item | Detail |
| --- | --- |
| `spec.md` | The ACs are the source of truth. |
| Diff surface | The commit range for the feature. |
| Test files in scope | What the coverage claim rests on. |
| `validate.md` | Its operating checklist, from the sibling skill. |

Three constraints, all load-bearing:

- **Author is not verifier.** A fresh executor that did not write the code. An
  author re-checking its own work reapplies the blind spot that produced the
  gap.
- **Read-only on the real tree.** It may not modify code or tests
  (LOOP-04 AC 2). Its discrimination sensor mutates only in a scratch copy,
  which is then discarded.
- **It does not fix.** Findings go back to a separate `fix` stage.

**Returns:** a verdict of PASS or FAIL, per-AC evidence with `file:line`
citations, the sensor result, and a ranked gap list. It writes
`validation.md`; the orchestrator records the verdict through
`update_loop.py`.

### Fix implementer

Consumes the ranked gaps from a FAIL round.

| Item | Detail |
| --- | --- |
| Ranked gaps | From `validation.md`, verbatim. |
| The ACs they violate | So a fix targets the requirement, not the symptom. |
| Diff surface | The code in question. |
| Gate commands | Same gates as the batch worker. |

It is a **different executor from the verifier** - that separation is the
reason `fix` is its own phase rather than a step inside verify, and it is what
lets the two run on different providers.

It fixes and reports. It does not declare itself verified: the verifier runs
again afterwards, and that re-run is what closes the round.

---

## Evidence per provider

What the loop reads to confirm the work happened. From
[providers.md](providers.md).

| Provider | Channel | Confirmed by |
| --- | --- | --- |
| `claude` (native) | Sub-agent return value | The report the harness returns. |
| `claude` (CLI) | stdout, `--output-format stream-json` | Captured stream, plus the evidence file if the payload asked for one. |
| `codex` | `-o/--output-last-message <FILE>` | The file exists and is non-empty. |
| `cursor` | stdout, `--output-format json` | Parsed result object. |
| custom | Whatever `{evidence}` names | The file exists and is non-empty. |

`codex` has the strongest channel: a real file at a path the loop chose, which
can be checked without parsing a stream. Prefer an explicit `{evidence}` file
for any custom provider for the same reason.

---

## Timeouts and failure

### Timeout

`limits.executor_timeout_seconds` in `loop.config.toml` bounds a single
invocation. Omitted means unlimited (TOML has no null, D8).

**A timeout is an executor failure, not a retry condition.** On expiry the loop
kills the process and halts with `phase=H reason=executor`, naming the command.

A non-interactive agent that hangs produces exactly what a slow one produces:
nothing. There is no signal that distinguishes them, so without a bound an
overnight run stalls until a human notices - which is precisely the failure
mode unattended execution exists to remove. Partial output is kept for
diagnosis and never counted as completion.

Set this before leaving a run unattended.

### Launch, authentication, and quota

A CLI that is missing, unauthenticated, or out of quota halts with
`phase=H reason=executor` and the command recorded, so the provider can be
changed in config and the run resumed (LOOP-05 AC 5). These are not repairable
from inside the loop: no amount of retrying fixes an expired token.

This is not hypothetical. The codex probe in
[provider-discovery.md](provider-discovery.md) returned
`ERROR: You've hit your usage limit` mid-session. Under a real run that is a
halt with the reason recorded, not a stuck loop.

### What is repairable

| Symptom | Handling |
| --- | --- |
| Gate failed on a task | Repair inside the phase. Diagnose first; a bare rerun is not a repair. |
| Evidence missing, executor claims done | Phase stays open, re-collect or re-run the lane. |
| Executor committed despite rule 1 | Phase stays open, work preserved, ownership repaired. |
| Same task's gate failed past its limit | `phase=H reason=gate_stuck`. |
| CLI missing, auth expired, quota, timeout | `phase=H reason=executor`. |

---

## `herdr` is an ordinary `command` executor

`cy-loop-tasks` treated `herdr` as a built-in dependency. Here it is one
provider entry among others, and the loop has no herdr-specific code path:

```toml
[providers.herdr]
kind = "command"
command = "herdr run --repo {repo} --model {model} --out {evidence} {prompt}"

[stages.implement]
provider = "herdr"
model = "gpt-5.6-luna"
```

Same placeholders, same two universal rules, same timeout, same evidence
contract. It never commits, and its evidence is verified rather than trusted,
exactly like every other executor.

Nothing about the loop assumes it exists. Any orchestrator that accepts a
prompt and writes a result file drops into the same slot.
