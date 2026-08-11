# Halt Resume Specification

## Problem Statement

`update_loop.py` can write a halt into `loop.json` but has no route to clear
one. Once `halt.reason` is set, `detect_phase.py` returns it before any other
condition is evaluated (`scripts/detect_phase.py:85-87`), so the run stays at
`phase=H` forever. `--status active` moves only `status`, leaving a state file
that claims to be active while still carrying a halt. The only remaining exit
is deleting `loop.json`, which discards the immutable objective, the counters,
the clock, the iteration history, the Verify state, and the reconciliations.

The docs already promise the missing operation. `references/phase-transitions.md:252`
says a halt "clears only by a human resolving the cause and clearing
`halt.reason`", while `references/state-schema.md:12` says the file is
machine-owned and must not be hand-edited. No API satisfies both.

A second defect produces the states that get stuck. `counters.gate_attempts` is
what `limits.gate_attempts_per_task` bounds (`scripts/detect_phase.py:100-104`),
but no shipped instruction ever calls `update_loop.py --gate-attempt`.
`references/recovery-loop.md:13` states that a repairable failure moves no
counter, and `:25` states that an intermediate failure never calls
`update_loop.py`. The counter therefore has no writer, stays `{}`, and a
`gate_stuck` halt can only be recorded by hand - which is exactly how an
unrecoverable halt with an empty counter appears.

## Goals

- [ ] A recorded halt can be lifted through the single writer, with the
      objective, counters, Verify state, and iteration history intact.
- [ ] A halt whose cause still holds re-fires on the next detection, so
      resuming is not a way to bypass a limit.
- [ ] `counters.gate_attempts` has exactly one documented writer, so
      `limits.gate_attempts_per_task` bounds something real.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Auto-resume by the loop itself | `H` is terminal by design (`SKILL.md:363`). Lifting a halt is a human decision; automating it removes the stop. |
| Resetting `counters.gate_attempts` on resume | Zeroing the counter converts the halt into an infinite retry budget. Resolving the cause or editing the config is the intended exit. |
| Changing the halt precedence in `detect_phase.py` | A recorded halt outranking derived work is correct. The defect is the absent inverse operation, not the ordering. |
| Making `loop.json` hand-editable | The machine-owned rule stays. This feature adds the API the rule presumes. |
| A `--resume` flag on `detect_phase.py` or `loop.sh` | `update_loop.py` is the only mutator after bootstrap (`scripts/update_loop.py:2-6`). A second writer would break that invariant. |
| Retroactively repairing existing stuck `loop.json` files | The new flag handles them at runtime; no migration step is added. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Which statuses `--resume` accepts | Any status except `complete`, provided `halt.reason` is non-null | The user chose "`halted` or `blocked`". Both are covered. `active` with a non-null `halt.reason` is also accepted because it is the incoherent state today's `--status active` produces - refusing it would leave existing wreckage unrecoverable, which is the bug being fixed. `complete` is refused: a finished run has nothing to resume. | y |
| Flag name | `--resume` | Named in the defect report; describes the transition rather than the field it touches. | y |
| Whether resume bumps `iteration` | No | `iteration` feeds `limits.max_iterations`. Bumping it would let resuming a run walk it into a `limit` halt. | n |
| Whether resume increments `iterations_without_commit` | No | That counter feeds `no_progress`. Incrementing on resume could re-halt the run on the very next detection for a reason the resume did not cause. | n |
| Where the resume is recorded | One appended entry in `iterations`, subject to the existing `LOG_LIMIT` trim | The log is the append-only audit trail; a state transition that leaves no trace is unauditable. | n |
| `--detail` reused as the resume note | Yes | It is already the free-text field of this CLI. A second text flag for the same purpose is redundant surface. | n |
| Which phase B step records a gate attempt | The failed gate, before the repair loop is entered | `gate_attempts_per_task` counts attempts per task; the count must move when the attempt fails, not when the repair succeeds. | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Lift a recorded halt ⭐ MVP

**User Story**: As an operator of a halted run, I want to clear the recorded
halt through the loop's own writer so that I can continue after resolving the
cause without deleting `loop.json` and losing the run.

**Why P1**: Without it the only exit is destroying state that git does not
hold. Everything else in this spec is secondary to restoring that exit.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHILE `halt.reason` is non-null and `status` is not `complete`, WHEN `update_loop.py <feature> --resume` is invoked THEN update_loop.py SHALL write `halt` as `{"reason": null, "detail": null}` and exit 0.
2. WHILE `halt.reason` is non-null and `status` is not `complete`, WHEN `update_loop.py <feature> --resume` is invoked THEN update_loop.py SHALL set `status` to `active`.
3. WHEN `--resume` is invoked THEN update_loop.py SHALL leave `objective`, `counters` (including `gate_attempts` and `iterations_without_commit`), `verify`, `reconciled`, `current_batch`, `current_task`, and `iteration` equal to their pre-invocation values.
4. WHEN `--resume` is invoked THEN update_loop.py SHALL append exactly one entry to `iterations` whose `phase` is `"H"`, whose `action` starts with `"resume"`, and whose `action` contains the `--detail` text when one was passed.
5. IF `halt.reason` is null THEN update_loop.py SHALL exit 2 with a stderr message naming that no halt is recorded, and SHALL leave `loop.json` byte-identical.
6. IF `status` is `complete` THEN update_loop.py SHALL exit 2 with a stderr message naming the status, and SHALL leave `loop.json` byte-identical.
7. IF `--resume` and `--halt` appear in the same invocation THEN update_loop.py SHALL exit 2 with a stderr message naming the contradiction, and SHALL leave `loop.json` byte-identical.
8. The system SHALL treat `--resume` as an action flag, so an invocation carrying only `--resume` is never rejected as a no-op.
9. WHILE a derived halt condition still holds after a resume, WHEN `detect_phase.py` runs THEN it SHALL print `phase=H` with the derived reason rather than a work phase.
10. WHILE no halt condition holds after a resume, WHEN `detect_phase.py` runs THEN it SHALL print the work phase the run's git and task state imply.

**Independent Test**: Record a halt, run `--resume`, and confirm
`detect_phase.py` leaves `phase=H` while `loop.json` still holds the original
objective, counters, and iteration count.

---

### P2: Give `gate_attempts` a documented writer

**User Story**: As an operator relying on `limits.gate_attempts_per_task`, I
want the shipped instructions to name when a failed gate is recorded so that
the limit bounds a counter something actually writes.

**Why P2**: The limit is live config today but reads a counter with no writer,
so `gate_stuck` can only arrive by hand. P1 restores the exit; P2 removes the
reason operators land there.

**Acceptance Criteria**:

1. WHEN a task's gate fails in Phase B THEN SKILL.md SHALL name the `update_loop.py <feature> --root <root> --gate-attempt <TN>` call that records the failure.
2. WHERE `references/recovery-loop.md` states that an intermediate failure moves no counter, it SHALL name the failed gate as the one exception and point at the Phase B step that writes it.
3. IF SKILL.md stops naming `--gate-attempt` THEN `test_unit_docs_parity.py` SHALL fail with a message naming `SKILL.md`.
4. IF `references/recovery-loop.md` stops naming `--gate-attempt` THEN `test_unit_docs_parity.py` SHALL fail with a message naming that file.

**Independent Test**: Delete the `--gate-attempt` instruction from SKILL.md and
confirm the docs-parity suite fails naming the file.

---

### P3: Document the resume transition

**User Story**: As a reader of the shipped docs, I want the halt-clearing
sentence to name the command so that the machine-owned rule and the
halt-clearing rule stop contradicting each other.

**Why P3**: The behavior ships with P1; this makes the prose agree with it.
Kept separate so a doc miss cannot masquerade as a behavior miss.

**Acceptance Criteria**:

1. WHEN `references/phase-transitions.md` describes how a halt clears THEN it SHALL name `update_loop.py --resume` as the operation, alongside resolving the cause or changing the config.
2. WHEN `references/state-schema.md` documents the `halt` field THEN it SHALL name `--resume` as the writer that clears it.
3. WHEN SKILL.md describes Phase H THEN it SHALL name `--resume` as the way a human lifts the halt.
4. IF any shipped document still states that clearing a halt requires editing `halt.reason` by hand THEN `test_unit_docs_parity.py` SHALL fail naming the file and line.

**Independent Test**: Grep the shipped docs for the hand-edit phrasing and
confirm the parity suite flags a planted reintroduction.

---

## Edge Cases

- IF `--resume` is combined with `--status blocked` THEN the explicit status SHALL win over the resume default, matching the existing rule that an explicit `--status` is applied last (`scripts/update_loop.py:191-195`).
- IF `--resume` is combined with `--iteration-done` THEN update_loop.py SHALL record both the resume entry and the closed iteration, and `iteration` SHALL advance by exactly 1.
- IF `loop.json` cannot be read THEN `--resume` SHALL exit 1 like every other action, since a state that cannot be parsed cannot be resumed.
- WHEN `--resume` appends the entry that exceeds `LOG_LIMIT` THEN `iterations` SHALL keep the last 50 entries, matching the existing trim.
- IF `--resume` is invoked twice in a row THEN the second call SHALL exit 2 under AC 5, because the first already cleared `halt.reason`.

---

## Requirement Traceability

| Requirement ID | Story | Covers | Phase | Status |
| -------------- | ----- | ------ | ----- | ------ |
| RESUME-01 | P1: Lift a recorded halt | P1 AC 1, 2, 8 - the transition itself and its flag registration | T1 | Implementing |
| RESUME-02 | P1: Lift a recorded halt | P1 AC 3, 4 - preservation of state and the audit entry | T2 | Pending |
| RESUME-03 | P1: Lift a recorded halt | P1 AC 5, 6, 7 - the three refusals, each leaving the file untouched | T1 | Implementing |
| RESUME-04 | P1: Lift a recorded halt | P1 AC 9, 10 - derived conditions re-evaluated after a resume | Tasks | Pending |
| RESUME-05 | P2: Give `gate_attempts` a documented writer | P2 AC 1-4 - the documented writer and its parity guard | Tasks | Pending |
| RESUME-06 | P3: Document the resume transition | P3 AC 1-4 - the prose agreeing with the behavior | Tasks | Pending |

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 6 total, 0 mapped to tasks, 6 unmapped ⚠️

---

## Success Criteria

- [ ] The reproduction in the defect report ends at a work phase instead of `phase=H`, with `objective`, `counters`, and `iteration` unchanged from before the halt.
- [ ] A run halted by a still-true derived condition re-halts on the detection following a resume.
- [ ] `python3 -m unittest discover -s scripts -p 'test_*.py'` passes with the new cases included.
- [ ] No shipped document instructs a reader to clear `halt.reason` by hand.
