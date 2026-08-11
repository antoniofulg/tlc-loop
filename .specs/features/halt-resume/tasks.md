# Halt Resume Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/halt-resume/spec.md`
**Design**: none - no architectural decision. `--resume` is an additive flag on the existing single writer.
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: **none** - no `AGENTS.md`, `CONTRIBUTING.md`, `Makefile`, `pyproject.toml`, or CI workflow. Inherited from `.specs/features/tlc-loop/tasks.md`, with one row corrected: prose is no longer untested. `scripts/test_unit_docs_parity.py` now asserts prose-to-code parity, so a documentation change ships with a test like any other layer.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| CLI entrypoint (`update_loop`, `detect_phase`) | unit | Every printed output variant and every non-zero exit path, invoked as a subprocess inside a tmpdir git repo | `scripts/test_unit_*.py` | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |
| Cross-script flow (halt → resume → detect) | integration | The full transition over a real tmpdir git repo, both when the cause is resolved and when it still holds | `scripts/test_int_*.py` | `python3 -m unittest discover -s scripts -p 'test_int_*.py'` |
| Prose (`SKILL.md`, `references/`) | unit | Every instruction this feature adds is asserted by a parity test that fails naming the file when the instruction is removed | `scripts/test_unit_docs_parity.py` | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |

**Baseline (measured before Execute):** 463 unit tests, 540 total, all passing. Quick gate ~161s, full gate ~194s - both exceed a 120s command timeout, so gates run with an extended timeout.

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |
| Full | After tasks with integration tests | `python3 -m unittest discover -s scripts -p 'test_*.py'` |
| Build | After phase completion or prose-only tasks | `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'` |

**Tools note:** no MCP server is required. Every task uses filesystem and shell access only.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: The transition

The behavior itself. Nothing downstream can be documented until the flag exists.

```
T1 → T2 → T3
```

### Phase 2: The documented writer

Closes the cause that strands runs at `gate_stuck` with an empty counter.

```
T4 → T5
```

### Phase 3: The prose agrees

Documentation catches up to the behavior. Ordered so the retracted-claim needle lands only after every document it scans is already clean.

```
T6 → T7 → T8
```

---

## Task Breakdown

### T1: Add `--resume` and its guard to `update_loop.py` ✅

**What**: Add the `--resume` flag, register it as an action flag, guard it with a `_not_resumable` refusal that runs before `apply()`, and clear `halt` while setting `status` to `active`.
**Where**: `scripts/update_loop.py`
**Depends on**: None
**Reuses**: `_not_completable` (`scripts/update_loop.py:109`) as the refusal-before-apply pattern; `ACTION_FLAGS` (`:59`); the exit-code contract in the module docstring (`:24`).
**Requirement**: RESUME-01, RESUME-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `--resume` exists in the parser and in `ACTION_FLAGS`, so `--resume` alone is not rejected as a no-op (spec P1 AC 8)
- [ ] With `halt.reason` non-null and `status` not `complete`, `--resume` writes `halt` as `{"reason": null, "detail": null}` and exits 0 (P1 AC 1)
- [ ] The same invocation sets `status` to `active` (P1 AC 2)
- [ ] `--resume` with `halt.reason` null exits 2, names that no halt is recorded on stderr, and leaves `loop.json` byte-identical (P1 AC 5)
- [ ] `--resume` on a `complete` run exits 2, names the status, and leaves `loop.json` byte-identical (P1 AC 6)
- [ ] `--resume` together with `--halt` exits 2, names the contradiction, and leaves `loop.json` byte-identical (P1 AC 7)
- [ ] `--resume` with an unreadable `loop.json` exits 1, matching every other action (spec Edge Cases)
- [ ] `--resume --status blocked` leaves `status` as `blocked`, because an explicit status is applied last (spec Edge Cases)
- [ ] Unit tests added to `scripts/test_unit_update_loop.py` cover each bullet above, including a byte-identity assertion on the file for all three refusals
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 473 unit tests pass (baseline 463 + ≥10 new), no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `feat(update-loop): add --resume to lift a recorded halt`

---

### T2: Record the resume in the append-only iteration log ✅

**What**: Extract the append-and-trim of `iterations` so `--resume` appends exactly one audit entry without incrementing `iteration` or `iterations_without_commit`.
**Where**: `scripts/update_loop.py`
**Depends on**: T1
**Reuses**: the existing append + `del state["iterations"][:-LOG_LIMIT]` trim (`scripts/update_loop.py:207-219`); `LOG_LIMIT` (`:38`).
**Requirement**: RESUME-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `--resume` appends exactly one entry to `iterations` with `phase` `"H"` and an `action` starting with `"resume"` (P1 AC 4)
- [ ] The entry's `action` contains the `--detail` text when one was passed, and omits it cleanly when none was (P1 AC 4)
- [ ] `--resume` leaves `objective`, `counters.gate_attempts`, `counters.iterations_without_commit`, `verify`, `reconciled`, `current_batch`, `current_task`, and `iteration` equal to their pre-invocation values (P1 AC 3)
- [ ] A resume that pushes `iterations` past `LOG_LIMIT` keeps the last 50 entries (spec Edge Cases)
- [ ] `--resume --iteration-done` records both the resume entry and the closed iteration, advancing `iteration` by exactly 1 (spec Edge Cases)
- [ ] A second consecutive `--resume` exits 2 under the no-halt-recorded refusal (spec Edge Cases)
- [ ] Unit tests added to `scripts/test_unit_update_loop.py` cover each bullet above
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 479 unit tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `feat(update-loop): record the resume in the append-only log`

---

### T3: Cover halt, resume, and the re-derived halt end to end ✅

**What**: Add an integration test that walks halt → resume → detect over a real tmpdir git repo, proving a still-true derived condition re-halts and a resolved one does not.
**Where**: `scripts/test_int_end_to_end.py`
**Depends on**: T2
**Reuses**: the tmpdir git-repo fixtures already in `scripts/test_int_end_to_end.py`.
**Requirement**: RESUME-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A recorded halt followed by `--resume` returns `detect_phase.py` to the work phase the run's git and task state imply (P1 AC 10)
- [ ] A resume taken while `gate_attempts` still exceeds `limits.gate_attempts_per_task` produces `phase=H reason=gate_stuck` on the next detection (P1 AC 9)
- [ ] A resume taken while `iterations_without_commit` still exceeds `limits.no_progress_iterations` produces `phase=H reason=no_progress` on the next detection (P1 AC 9)
- [ ] The reproduction from the defect report ends at a work phase with `objective`, `counters`, and `iteration` unchanged from before the halt (spec Success Criteria)
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_*.py'`
- [ ] Test count: ≥ 560 total tests pass, no existing test deleted or weakened

**Tests**: integration
**Gate**: full

**Commit**: `test(loop): cover halt, resume, and the re-derived halt`

---

### T4: Record a failed gate attempt in Phase B ✅

**What**: Add the Phase B step that calls `update_loop.py --gate-attempt <TN>` when a task's gate fails, and the parity test that fails naming `SKILL.md` if the instruction is removed.
**Where**: `SKILL.md`
**Depends on**: None
**Reuses**: the Phase B step list (`SKILL.md:219-278`); the parity-test structure in `scripts/test_unit_docs_parity.py` (`shipped_documents`, `offending_lines`).
**Requirement**: RESUME-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Phase B names the exact `python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> --gate-attempt <TN>` call for a failed gate (P2 AC 1)
- [ ] The instruction states the call happens on the failed attempt, before the repair loop is entered, so the counter tracks attempts rather than repairs (spec Assumptions)
- [ ] A test in `scripts/test_unit_docs_parity.py` fails with a message naming `SKILL.md` when the instruction is absent (P2 AC 3)
- [ ] That test is proven to discriminate: it passes on the shipped text and fails on a planted copy with the instruction removed
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 481 unit tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `docs(skill): record a failed gate attempt in phase B`

---

### T5: Name the failed gate as the counter exception ✅

**What**: Amend the "no counter moves" and "never calls `update_loop.py`" rules to name the failed gate as the single exception, pointing at the Phase B step from T4, and guard it with a parity test.
**Where**: `references/recovery-loop.md`
**Depends on**: T4
**Reuses**: the repair-loop opening (`references/recovery-loop.md:12-25`); the parity-test structure from T4.
**Requirement**: RESUME-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The "no counter moves" rule (`:13`) and the "never calls `update_loop.py`" rule (`:25`) both name `--gate-attempt` as the one exception and point at the Phase B step (P2 AC 2)
- [ ] The `gate_stuck` row of the failure table (`:95`) reads consistently with the new exception
- [ ] A test in `scripts/test_unit_docs_parity.py` fails with a message naming `references/recovery-loop.md` when the exception is absent (P2 AC 4)
- [ ] That test is proven to discriminate against a planted copy with the exception removed
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 483 unit tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `docs(recovery): name the failed gate as the counter exception`

---

### T6: Name `--resume` as the writer that clears `halt` ✅

**What**: Document `--resume` as the writer of the `halt` field in the state schema, so the machine-owned rule and the halt-clearing rule stop contradicting each other.
**Where**: `references/state-schema.md`
**Depends on**: None
**Reuses**: the field table that already names a writer per field (`references/state-schema.md:118`); the halt reason table (`:273`).
**Requirement**: RESUME-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The `halt` field documentation names `--resume` as the operation that clears it (P3 AC 2)
- [ ] The machine-owned paragraph (`:12`) points at `--resume` instead of leaving the reader with no supported exit
- [ ] The existing `## What deleting the file costs` section still names `objective`, `counters`, `verified_at`, `halt`, and `reconciled`, so `test_state_schema_says_what_deleting_the_file_does_cost` keeps passing
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 483 unit tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `docs(state-schema): name --resume as the halt clearer`

---

### T7: Name `--resume` in the halt phase ✅

**What**: Amend the Phase H branch so the "a halt does not clear itself" rule names the command a human runs after resolving the cause.
**Where**: `SKILL.md`
**Depends on**: T6
**Reuses**: the Phase H branch (`SKILL.md:363-386`).
**Requirement**: RESUME-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Phase H names `python3 <skill-dir>/scripts/update_loop.py <feature> --root <root> --resume` as how a human lifts the halt (P3 AC 3)
- [ ] The rule that the loop never resumes itself is preserved verbatim in meaning - `--resume` is a human action, not a loop step
- [ ] The halt-reason enumeration in Phase H is untouched, so `test_skill_md_enumerates_exactly_the_implemented_reasons` keeps passing
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 483 unit tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `docs(skill): name --resume in the halt phase`

---

### T8: Replace the hand-edit halt clearing with `--resume`

**What**: Rewrite the transition-table row that tells a human to clear `halt.reason` by hand, and add that phrasing to the retracted-claim scan so it cannot return.
**Where**: `references/phase-transitions.md`
**Depends on**: T7
**Reuses**: `RETRACTED_CLAIMS` and the `test_no_shipped_document_repeats_a_retracted_claim` scan (`scripts/test_unit_docs_parity.py:159`).
**Requirement**: RESUME-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The `H` row (`references/phase-transitions.md:252`) names `update_loop.py --resume` alongside resolving the cause or changing the config (P3 AC 1)
- [ ] The hand-edit phrasing is added to `RETRACTED_CLAIMS`, so any shipped document reasserting it fails the scan naming the file and line (P3 AC 4)
- [ ] `test_a_reintroduced_claim_is_named_with_its_location` covers the new needle, proving the scan discriminates
- [ ] No shipped document trips the extended scan
- [ ] Gate check passes: `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- [ ] Test count: ≥ 561 total tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: build

**Commit**: `docs(transitions): replace the hand-edit halt clearing with --resume`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 ------→ T2 ------→ T3
Phase 2:  T4 ------→ T5
Phase 3:  T6 ------→ T7 ------→ T8
```

Execution is strictly sequential - there is no intra-phase parallelism. 8 tasks pack into a single ~7-task batch, so Execute runs inline in the main window with no sub-agents dispatched. The Verifier still runs after the final task, as always.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `--resume` flag + guard | 1 file, 1 transition | ✅ Granular |
| T2: resume audit entry | 1 file, 1 extraction | ✅ Granular |
| T3: end-to-end coverage | 1 test file | ✅ Granular |
| T4: Phase B gate-attempt step | 1 doc section + its guard | ✅ Granular |
| T5: recovery-loop exception | 1 doc section + its guard | ✅ Granular |
| T6: state-schema halt writer | 1 doc file | ✅ Granular |
| T7: Phase H names `--resume` | 1 doc section | ✅ Granular |
| T8: transition row + needle | 1 doc row + 1 needle list | ✅ Granular |

T1 is not split into "add the flag" and "add the guard": a commit where `--resume` exists unguarded is a broken intermediate state, not an atomic deliverable.

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | phase-1 head | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | phase-2 head | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | None | phase-3 head | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |

No dependency points to a later phase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | CLI entrypoint (`update_loop`) | unit | unit | ✅ OK |
| T2 | CLI entrypoint (`update_loop`) | unit | unit | ✅ OK |
| T3 | Cross-script flow | integration | integration | ✅ OK |
| T4 | Prose (`SKILL.md`) | unit | unit | ✅ OK |
| T5 | Prose (`references/recovery-loop.md`) | unit | unit | ✅ OK |
| T6 | Prose (`references/state-schema.md`) | unit | unit | ✅ OK |
| T7 | Prose (`SKILL.md`) | unit | unit | ✅ OK |
| T8 | Prose (`references/phase-transitions.md`) | unit | unit | ✅ OK |

No task carries `Tests: none`. T6 and T7 add no new parity test of their own: both are asserted by the extended retracted-claim scan that T8 lands, and each carries its own regression guard in the `Done when` bullets naming the existing parity tests that must keep passing.

---

## Requirement Coverage

| Requirement ID | Tasks | Status |
| --- | --- | --- |
| RESUME-01 | T1 | Verified in T1 |
| RESUME-02 | T2 | Verified in T2 |
| RESUME-03 | T1 | Verified in T1 |
| RESUME-04 | T3 | Verified in T3 |
| RESUME-05 | T4, T5 | Verified in T4+T5 |
| RESUME-06 | T6, T7, T8 | Pending |

**Coverage:** 6 total, 6 mapped to tasks, 0 unmapped.
