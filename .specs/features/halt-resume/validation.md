# Halt Resume Validation

## Validation: halt-resume - FAIL ❌

**Date**: 2026-08-11
**Spec**: `.specs/features/halt-resume/spec.md`
**Diff range**: `main...HEAD` = `4a0345c..034612b` (8 commits, branch `fix/halt-resume-transition`)
**HEAD**: `034612b112aaef7a04d1d886c5cf4955b8beea50`
**Verifier**: independent sub-agent (author ≠ verifier), read-only over the real tree

**Verdict**: ❌ **FAIL** — behaviour is complete and fully discriminating; three
P3 documentation ACs are asserted at whole-file scope while the spec words them
at section scope, and three placement mutations survive as a result.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 `--resume` + guard | ✅ Done | `scripts/update_loop.py:71,104-108,140-157,240-250,289-294,315-319` |
| T2 resume audit entry | ✅ Done | `_log` extracted at `scripts/update_loop.py:160-179`, reused at `:250` and `:267-273` |
| T3 end-to-end coverage | ✅ Done | `scripts/test_int_end_to_end.py:458-535` |
| T4 Phase B gate-attempt step | ✅ Done | `SKILL.md:247-258`; guard `scripts/test_unit_docs_parity.py:415-430` |
| T5 recovery-loop exception | ✅ Done | `references/recovery-loop.md:17-22,32-35,104`; guard `scripts/test_unit_docs_parity.py:432-454` |
| T6 state-schema halt writer | ⚠️ Partial | Prose landed (`references/state-schema.md:272-293`); the guard does not bind it to the `halt` section — see Gap 2 |
| T7 Phase H names `--resume` | ⚠️ Partial | Prose landed (`SKILL.md:387-398`); the guard does not bind it to Phase H — see Gap 1 |
| T8 transition row + needle | ⚠️ Partial | Row rewritten (`references/phase-transitions.md:252`), needle added (`scripts/test_unit_docs_parity.py:342-347`); the row itself is not bound — see Gap 3 |

---

## Spec-Anchored Acceptance Criteria

### P1: Lift a recorded halt ⭐ MVP

| Criterion | Spec-defined outcome | `file:line` + assertion expression | Result |
| --- | --- | --- | --- |
| AC 1 — `--resume` writes `halt` as `{reason: null, detail: null}`, exit 0 | exactly that dict; rc 0 | `scripts/test_unit_update_loop.py:555` `self.assertEqual(_run(root, "--resume").returncode, 0)` + `:556` `self.assertEqual(_read(root)["halt"], {"reason": None, "detail": None})` | ✅ PASS |
| AC 2 — sets `status` to `active` | `"active"` | `scripts/test_unit_update_loop.py:562` `self.assertEqual(_read(root)["status"], "active")` | ✅ PASS |
| AC 3 — `objective`, `counters`, `verify`, `reconciled`, `current_batch`, `current_task`, `iteration` unchanged | byte-equal to pre-invocation values | `:640` `self.assertEqual(_read(root)["counters"], counters)` (with `gate_attempts={"T1":4}`, `iterations_without_commit=7`); `:646` `self.assertEqual(_read(root)["iteration"], 9)`; `:658-662` `assertEqual(after["objective"], OBJECTIVE)`, `assertEqual(after["verify"], verify)`, `assertEqual(after["reconciled"], reconciled)`, `assertEqual(after["current_batch"], ["T5","T6"])`, `assertEqual(after["current_task"], "T5")` | ✅ PASS |
| AC 4 — exactly one `iterations` entry, `phase == "H"`, `action` starts `"resume"`, carries `--detail` | 1 entry; `"H"`; prefix `resume`; detail substring | `:607` `assertEqual(len(_read(root)["iterations"]), 1)`; `:613` `assertEqual(...["phase"], "H")`; `:619` `assertTrue(...["action"].startswith("resume"))`; `:625-626` `assertIn("human approved another cycle", ...["action"])`; `:632` `assertEqual(...["action"], "resume")` | ✅ PASS |
| AC 5 — `halt.reason` null → exit 2, stderr names no halt, file byte-identical | rc 2; "no halt"; identical bytes | `:704-706` `assertEqual(proc.returncode, 2)` + `assertIn("no halt", proc.stderr)` + `assertEqual(_bytes(root), before)` | ✅ PASS |
| AC 6 — `status` `complete` → exit 2, stderr names the status, byte-identical | rc 2; "complete"; identical bytes | `:713-715` `assertEqual(proc.returncode, 2)` + `assertIn("complete", proc.stderr)` + `assertEqual(_bytes(root), before)` | ✅ PASS |
| AC 7 — `--resume` + `--halt` → exit 2, stderr names the contradiction, byte-identical | rc 2; both flags named; identical bytes | `:722-725` `assertEqual(proc.returncode, 2)` + `assertIn("--resume", proc.stderr)` + `assertIn("--halt", proc.stderr)` + `assertEqual(_bytes(root), before)` | ✅ PASS |
| AC 8 — `--resume` is an action flag; alone it is never a no-op | rc 0, no "nothing to do" | `:585-586` `assertEqual(proc.returncode, 0)` + `assertNotIn("nothing to do", proc.stderr)`; impl `scripts/update_loop.py:71` | ✅ PASS |
| AC 9 — derived halt still true after resume → `phase=H` with the derived reason | `phase=H action=halt reason=gate_stuck` / `reason=no_progress` | `scripts/test_int_end_to_end.py:509-510` `assertTrue(line.startswith("phase=H action=halt reason=gate_stuck "))` + `assertIn("T1", line)`; `:522` `assertTrue(line.startswith("phase=H action=halt reason=no_progress "))` | ✅ PASS |
| AC 10 — no halt condition after resume → the work phase git/tasks imply | the same line detection printed before the halt | `scripts/test_int_end_to_end.py:469,476` `before = self.detect()` … `self.assertEqual(self.detect(), before)` | ✅ PASS |

**Assumption row 1 (`--resume` does NOT require `status == halted`)** — verified
against implementation and tests:

| Check | Evidence | Result |
| --- | --- | --- |
| Impl refuses only on `complete` and on absent `halt.reason`; no `halted` check | `scripts/update_loop.py:153-157` `if state.get("status") == "complete": …` / `if not (state.get("halt") or {}).get("reason"): …` / `return None` (docstring `:148-151` states the omission is deliberate) | ✅ matches |
| `blocked` + halt is resumable | `scripts/test_unit_update_loop.py:570-571` `assertEqual(_run(root,"--resume").returncode, 0)` + `assertEqual(_read(root)["status"], "active")` | ✅ covered |
| `active` + stale halt is resumable (the state today's `--status active` produces) | `scripts/test_unit_update_loop.py:578-579` `assertEqual(_run(root,"--resume").returncode, 0)` + `assertIsNone(_read(root)["halt"]["reason"])` | ✅ covered |
| ACs 1/2/5/6 consistent with the assumption | AC 1/2 guard on "`halt.reason` non-null and `status` not `complete`"; AC 5 keys on `halt.reason`; AC 6 keys on `complete`. No AC mentions `halted`. | ✅ consistent |
| Prose states it | `references/state-schema.md:290-293` "it does **not** require `status` to be `halted`" | ✅ consistent |

### P2: Give `gate_attempts` a documented writer

| Criterion | Spec-defined outcome | `file:line` + assertion expression | Result |
| --- | --- | --- | --- |
| AC 1 — Phase B names the `update_loop.py <feature> --root <root> --gate-attempt <TN>` call | the call, inside Phase B | `scripts/test_unit_docs_parity.py:424-430` `body = phase_section(read_shipped("SKILL.md"), "#### Phase B - Execute one batch")` + `assertIn("--gate-attempt", body)`; doc `SKILL.md:251` | ✅ PASS (see Observation 1 on precision) |
| AC 2 — `recovery-loop.md` names the failed gate as the one exception and points at Phase B | exception in both rules | `scripts/test_unit_docs_parity.py:436-447` `head, _, body = text.partition("## Repair loop")` + `assertIn("--gate-attempt", section)` for both halves; doc `references/recovery-loop.md:17-22,32-35` | ✅ PASS |
| AC 3 — SKILL.md dropping `--gate-attempt` fails parity naming `SKILL.md` | failure message names `SKILL.md` | `scripts/test_unit_docs_parity.py:416-421` `assertIn("--gate-attempt", read_shipped("SKILL.md"), "SKILL.md no longer names --gate-attempt…")` — empirically killed by M8 | ✅ PASS |
| AC 4 — `recovery-loop.md` dropping it fails parity naming that file | message names `references/recovery-loop.md` | `scripts/test_unit_docs_parity.py:442-447` `f"references/recovery-loop.md: {where} still forbids…"` — empirically killed by M15 | ✅ PASS |

### P3: Document the resume transition

| Criterion | Spec-defined outcome | `file:line` + assertion expression | Result |
| --- | --- | --- | --- |
| AC 1 — `phase-transitions.md` **where it describes how a halt clears** names `update_loop.py --resume` alongside resolving the cause / changing the config | the flag in the halt-clearing passage (the `H` row) | `scripts/test_unit_docs_parity.py:385-389` `assertIn("--resume", read_shipped(relative))` — **whole-file, unscoped**; doc `references/phase-transitions.md:252,264-268` | ❌ GAP (M14 survived) |
| AC 2 — `state-schema.md` **where it documents the `halt` field** names `--resume` as the writer that clears it | the flag inside the `## \`halt\`` section | `scripts/test_unit_docs_parity.py:385-389` — same whole-file assertion; doc `references/state-schema.md:272-293` | ❌ GAP (M12 survived) |
| AC 3 — SKILL.md **where it describes Phase H** names `--resume` as how a human lifts the halt | the flag inside the Phase H branch | `scripts/test_unit_docs_parity.py:385-389` — same whole-file assertion; doc `SKILL.md:387-398` | ❌ GAP (M11b survived) |
| AC 4 — any shipped doc reasserting the hand-edit fails parity naming file and line | offender list `"{file}:{line} ({claim!r}): {line}"`, empty on the shipped tree | `scripts/test_unit_docs_parity.py:353-365` `assertEqual(offenders, [], …)` over `HAND_CLEARED_HALT` (`:342-347`); discrimination proof `:367-375` `assertTrue(offenders)` + `assertIn("fake.md:1", offenders[0])` | ✅ PASS |

**Status**: ⚠️ 11/14 ACs matched their spec-defined outcome at spec scope; 3 P3
ACs are asserted more loosely than the spec words them.

---

## Edge Cases

| Edge case | `file:line` + assertion | Result |
| --- | --- | --- |
| `--resume` + `--status blocked` → explicit status wins | `scripts/test_unit_update_loop.py:592` `assertEqual(_read(root)["status"], "blocked")` (impl order `scripts/update_loop.py:240-255`) | ✅ |
| `--resume` + `--iteration-done` → both recorded, `iteration` +1 | `scripts/test_unit_update_loop.py:681-682` `assertEqual(len(after["iterations"]), 2)` + `assertEqual(after["iteration"], 1)` | ✅ |
| unreadable `loop.json` → `--resume` exits 1 | `scripts/test_unit_update_loop.py:740` `assertEqual(_run(root, "--resume").returncode, 1)` | ✅ |
| resume entry past `LOG_LIMIT` → last 50 kept | `scripts/test_unit_update_loop.py:672-674` `assertEqual(len(entries), 50)` + `assertEqual(entries[-1]["phase"], "H")` + `assertEqual(entries[0]["n"], 1)` | ✅ |
| second consecutive `--resume` → exit 2 under AC 5 | `scripts/test_unit_update_loop.py:688` `assertEqual(_run(root, "--resume").returncode, 2)` | ✅ |

All five listed edge cases are covered with spec-matching asserted values.

---

## Discrimination Sensor

**Isolation**: `git worktree add --detach` to a scratch path outside the repo.
No `git stash`; the real working tree was never mutated.

- Pre-sensor `git status --porcelain` (real tree): **empty (clean)**
- Post-sensor `git status --porcelain` (real tree): **empty (clean)** — matches
- HEAD before and after: `034612b112aaef7a04d1d886c5cf4955b8beea50`; worktree removed and pruned

Scratch baseline before mutating: `test_unit_update_loop.py` 78 tests OK,
`test_unit_docs_parity.py` 32 tests OK.

| # | File:line | Mutation | Suite | Killed? |
| --- | --- | --- | --- | --- |
| M1 | `scripts/update_loop.py:153-154` | `_not_resumable`: drop the `complete` check | unit | ✅ Killed (1 failure) |
| M2 | `scripts/update_loop.py:155-156` | `_not_resumable`: drop the `halt.reason` check | unit | ✅ Killed (3 failures) |
| M3 | `scripts/update_loop.py:246` | `apply()`: `--resume` clears `halt` but never sets `status = "active"` | unit | ✅ Killed (2 failures) |
| M4 | `scripts/update_loop.py:245-246` | `apply()`: `--resume` also zeroes `counters["gate_attempts"]` (**explicitly Out of Scope**) | unit | ✅ Killed (1 failure) |
| M4i | `scripts/update_loop.py:245-246` | same fault, integration suite | integration | ✅ Killed (1 failure) |
| M5 | `scripts/update_loop.py:250` | `apply()`: remove the `_log(...)` call from the resume branch | unit | ✅ Killed (3 failures, 4 errors) |
| M6 | `scripts/update_loop.py:289-294` | `main()`: remove the `--resume` + `--halt` contradiction check | unit | ✅ Killed (1 failure) |
| M7 | `scripts/update_loop.py:179` | `_log`: remove `del state["iterations"][:-LOG_LIMIT]` | unit | ✅ Killed (3 failures) |
| M9 | `scripts/update_loop.py:71` | `ACTION_FLAGS`: drop `"resume"` so `--resume` alone is a no-op | unit | ✅ Killed (10 failures, 4 errors) |
| M10 | `scripts/update_loop.py:254-255` | `apply()`: an explicit `--status` no longer wins over `--resume` | unit | ✅ Killed (1 failure) |
| M13 | `scripts/update_loop.py:245` | `apply()`: `--resume` clears `halt.reason` but keeps `halt.detail` | unit | ✅ Killed (1 failure) |
| M8 | `SKILL.md:247-258` | move the `--gate-attempt` step out of Phase B into Phase V | docs | ✅ Killed (1 failure) |
| M15 | `references/recovery-loop.md:17-22` | drop the `--gate-attempt` exception from the opening rule (kept in step 1) | docs | ✅ Killed (1 failure) |
| M11b | `SKILL.md:387-398` | move every `--resume` mention out of the Phase H branch into Phase 0 (flag still present in the file) | docs | ❌ **Survived** |
| M12 | `references/state-schema.md:272-293` | move the `--resume` documentation off the `## \`halt\`` section to the top of the file | docs | ❌ **Survived** |
| M14 | `references/phase-transitions.md:252` | strip `update_loop.py --resume` from the `H` transition row (still named at `:264-268`) | docs | ❌ **Survived** |

Survivor verification (proof each is a placement-only fault, not a removal):

- M11b: whole-file names `--resume` = **True**; Phase H branch names `--resume` = **False**; suite **OK**
- M12: whole-file names `--resume` = **True**; `## \`halt\`` section names `--resume` = **False**; suite **OK**
- M14: `--resume` still present at `references/phase-transitions.md:264-268`; the `H` row no longer names it; suite **OK**

**Sensor depth**: P0-full (16 mutations; ≥5 required)
**Result**: 13/16 killed, 3 survived - FAIL ❌

Behaviour layer alone: **11/11 killed**. P2 doc layer: **2/2 killed**. P3 doc
layer: **0/3 killed**.

---

## Gate Check

- **Gate command**: `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Exit code**: `0`
- **Result**: `Ran 575 tests in 188.473s` — **OK**. 575 passed, 0 failed, 0 skipped.
- **Test count before feature** (tasks.md measured baseline): 540 total (463 unit)
- **Test count after feature**: 575 total
- **Delta**: **+35 tests**
- Meets both tasks.md floors: T3 `≥ 560 total` ✅, T8 `≥ 561 total` ✅
- No test deleted; no assertion weakened (the diff is additive across all three
  test files — `+209`, `+80`, `+128` lines, `0` deletions)

---

## Defect-Report Reproduction

Run in an isolated temp dir with the two skills side by side, a real git repo,
and a valid `tasks.md`. Literal output:

```
=== 1. bootstrap ===
route:
  Phase 1: Foundation -> implement (claude/-)
  Phase 2: Wiring -> implement (claude/-)
  Phase 3: Polish -> implement (claude/-)
bootstrapped feature=toy harness=claude (named by --respawn)
state=.../repro/project/.specs/features/toy/loop.json
=== 2. detect (pre-halt) ===
phase=B action=execute_batch batch=P1+P2+P3 tasks=T1,T2,T3,T4,T5,T6 stage=implement
=== 3. halt ===
updated feature=toy iteration=0 status=halted
=== 4. detect (halted) ===
phase=H action=halt reason=gate_stuck detail="T1 exceeded its gate budget"
=== 5. state BEFORE resume ===
objective='ship toy'
counters={'gate_attempts': {}, 'iterations_without_commit': 0, 'started_at_ms': 1786456300034}
iteration=0
status='halted'
halt={'detail': 'T1 exceeded its gate budget', 'reason': 'gate_stuck'}
=== 6. resume ===
updated feature=toy iteration=0 status=active
exit=0
=== 7. detect (after resume) ===
phase=B action=execute_batch batch=P1+P2+P3 tasks=T1,T2,T3,T4,T5,T6 stage=implement
=== 8. state AFTER resume ===
objective='ship toy'
counters={'gate_attempts': {}, 'iterations_without_commit': 0, 'started_at_ms': 1786456300034}
iteration=0
status='active'
halt={'detail': None, 'reason': None}
iterations= [{"action": "resume: cause resolved", "at": "2026-08-11T13:51:40Z", "commit": null, "n": 0, "phase": "H", "task": null}]
=== 9. resume a second time ===
update_loop: refusing --resume: no halt is recorded
exit=2
```

Confirms Success Criterion 1: `phase=H` → `--resume` → `phase=B`, with
`objective`, `counters`, and `iteration` byte-identical across the halt and the
resume, one audit entry appended, and the second `--resume` refused with exit 2.

---

## Necessity Check (every new test maps to a spec requirement)

| New test (`file:line`) | Maps to |
| --- | --- |
| `test_unit_update_loop.py:552` the recorded reason and detail are cleared | P1 AC 1 |
| `:558` the run returns to active | P1 AC 2 |
| `:564` a blocked run carrying a halt is resumable | Assumptions row 1 |
| `:573` an active run carrying a stale halt is resumable | Assumptions row 1 |
| `:581` resume alone is not rejected as a no-op | P1 AC 8 |
| `:588` an explicit status wins over the resume default | Edge case 1 |
| `:603` exactly one entry is appended | P1 AC 4 |
| `:609` the entry is recorded against the halt phase | P1 AC 4 |
| `:615` the action names the transition | P1 AC 4 |
| `:621` the action carries the detail when one is given | P1 AC 4 |
| `:628` the action is bare when no detail is given | P1 AC 4 |
| `:634` the counters the halt conditions read are untouched | P1 AC 3 |
| `:642` the iteration number does not advance | P1 AC 3 |
| `:648` objective, verify and reconciled survive | P1 AC 3 |
| `:664` the log stays capped at the limit | Edge case 4 |
| `:676` a resume that also closes an iteration records both | Edge case 2 |
| `:684` a second consecutive resume is refused | Edge case 5 |
| `:699` no recorded halt is refused naming the absence | P1 AC 5 |
| `:708` a complete run is refused naming the status | P1 AC 6 |
| `:717` resume together with halt is refused as contradictory | P1 AC 7 |
| `:727` a refusal applies none of the other flags | P1 AC 5/6/7 (byte-identity), T1 Done-when |
| `:733` an unreadable state file exits one not two | Edge case 3 |
| `test_int_end_to_end.py:465` a resume returns the run to the phase its state implies | P1 AC 10 |
| `:478` the run survives the halt and the resume intact | P1 AC 3, Success Criteria 1 |
| `:498` a resume does not buy past the gate attempt limit | P1 AC 9 |
| `:512` a resume does not buy past the no progress limit | P1 AC 9 |
| `:524` raising the limit is what makes the resume stick | Success Criteria 2 / Out-of-Scope row 2 (control: proves the re-halt is the limit, not a failed clear) |
| `test_unit_docs_parity.py:353` no shipped document sends the reader to the field | P3 AC 4, Success Criteria 4 |
| `:367` a reintroduced instruction is named with its location | P3 AC 4 (discrimination) |
| `:377` the documents that describe the halt name the flag | P3 AC 1, 2, 3 (loosely — see gaps) |
| `:415` skill_md names the call that records a failed gate | P2 AC 3 |
| `:423` the call sits in the phase that runs the gate | P2 AC 1 |
| `:432` the recovery loop carves the exception in both rules | P2 AC 2, AC 4 |
| `:449` the partition separates the two rules it checks | anchor guard for `:432` |
| `:456` the section scan stops at the next phase | anchor guard for `phase_section` (`:392-403`) |

**Result**: 35/35 new tests map to a spec AC, a listed edge case, a Success
Criterion, or an anchor guard for one of those. **No scope creep found.**

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ `--resume` is one flag, one guard, one log entry |
| No abstractions for single-use code | ✅ `_log` (`update_loop.py:160-179`) has two call sites (`:250`, `:267`); extraction is justified, not speculative |
| No unnecessary "flexibility" added | ✅ no auto-resume, no counter reset, no second writer — all match the Out of Scope table |
| Only touched files required for task | ✅ 1 script, 4 docs, 3 test files, 2 spec files |
| Didn't "improve" unrelated code | ✅ the only refactor is the `_log` extraction T2 called for |
| Matches existing patterns/style | ✅ `_not_resumable` mirrors `_not_completable` (`:115-137`); refusal-before-`apply()` at `:315-319` mirrors `:309-313` |
| Would a senior engineer approve? | ✅ for the behaviour; ⚠️ the P3 parity guards are looser than the P2 ones the same author wrote |
| Tests map to ACs and are non-shallow | ✅ see Necessity Check |
| Spec-anchored outcome check | ⚠️ 11/14 — 3 P3 ACs asserted at whole-file scope (Gaps 1-3) |
| Per-layer Coverage Expectation met | ✅ CLI: every new output variant and non-zero exit path covered as a subprocess in a tmpdir; integration: both the resolved and still-true cause; prose: parity-guarded — except the three P3 scopes |
| Every test maps to a spec requirement | ✅ 35/35 |
| Documented guidelines followed | ✅ none exist (confirmed: no `AGENTS.md`, `CONTRIBUTING.md`, `Makefile`, `pyproject.toml`, CI workflow) — strong defaults applied |

---

## Fix Plans

### Fix 1 (Major): bind SKILL.md's `--resume` to the Phase H branch — P3 AC 3

- **Root cause**: `scripts/test_unit_docs_parity.py:377-389` asserts
  `assertIn("--resume", read_shipped("SKILL.md"))` over the whole document.
  Spec AC 3 scopes the requirement to "WHEN SKILL.md describes Phase H". The
  file already ships the right tool: `phase_section()` at
  `scripts/test_unit_docs_parity.py:392-403`, used for Phase B at `:423-430`.
- **Fix**: assert `--resume` inside
  `phase_section(read_shipped("SKILL.md"), "#### Phase H - Halt")`.
- **Verify**: re-run M11b — moving every `--resume` mention out of Phase H must
  fail the suite naming `SKILL.md`.

### Fix 2 (Major): bind `state-schema.md`'s `--resume` to the `halt` section — P3 AC 2

- **Root cause**: same whole-file assertion at
  `scripts/test_unit_docs_parity.py:385-389`. Spec AC 2 scopes it to "WHEN
  `references/state-schema.md` documents the `halt` field".
- **Fix**: partition on the `` ## `halt` `` heading (the pattern already used at
  `:436-441` for `recovery-loop.md`) and assert `--resume` in that section.
- **Verify**: re-run M12.

### Fix 3 (Major): bind `phase-transitions.md`'s `--resume` to the `H` row — P3 AC 1

- **Root cause**: same whole-file assertion. Spec AC 1 scopes it to "WHEN
  `references/phase-transitions.md` describes how a halt clears", i.e. the `H`
  transition row at `references/phase-transitions.md:252`.
- **Fix**: assert `--resume` on the line(s) beginning `| \`H\` |`, not on the file.
- **Verify**: re-run M14.

All three share one root cause and one edit site
(`scripts/test_unit_docs_parity.py:377-389`); no shipped prose needs to change.

---

## Observations (not gaps)

1. **P2 AC 1 / P3 AC 1 substring precision.** The spec names the full call
   `update_loop.py <feature> --root <root> --gate-attempt <TN>`, and AC 1 of P3
   asks for `--resume` "alongside resolving the cause or changing the config".
   The shipped prose satisfies both (`SKILL.md:251`,
   `references/phase-transitions.md:252`) but the assertions only match the flag
   substring. Lower severity than Gaps 1-3 because placement is guarded for P2.
2. **`--resume` + `--status complete`** is unspecified: `main()` runs
   `_not_completable` (`scripts/update_loop.py:309-313`) before `_not_resumable`
   (`:315-319`). Behaviour is sensible; no AC covers it. Not a gap.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| RESUME-01 (P1 AC 1, 2, 8) | Implementing | ✅ Verified |
| RESUME-02 (P1 AC 3, 4) | Implementing | ✅ Verified |
| RESUME-03 (P1 AC 5, 6, 7) | Implementing | ✅ Verified |
| RESUME-04 (P1 AC 9, 10) | Implementing | ✅ Verified |
| RESUME-05 (P2 AC 1-4) | Implementing | ✅ Verified |
| RESUME-06 (P3 AC 1-4) | Implementing | ❌ Needs Fix — AC 4 verified; ACs 1, 2, 3 asserted at whole-file scope, three placement mutants survive |

---

## Summary

**Overall**: ⚠️ Issues — the feature works; three P3 documentation guards are
weaker than the ACs they claim to enforce.

**Spec-anchored check**: 11/14 ACs matched the spec-defined outcome at spec scope; 3 P3 ACs under-scoped
**Sensor**: 16 mutations injected, **13 killed, 3 survived** (all 3 in the P3 doc-parity layer)
**Gate**: 575 passed, 0 failed, 0 skipped, exit 0
**Isolation**: pre- and post-sensor `git status --porcelain` both empty; HEAD unchanged at `034612b`

**What works**:

- Every P1 acceptance criterion, all five edge cases, and both Success Criteria
  1 and 2 trace to a `file:line` whose asserted value matches the spec.
- Assumption row 1 is honoured exactly: `_not_resumable`
  (`scripts/update_loop.py:140-157`) refuses only `complete` and an absent
  `halt.reason`, never requires `halted`, and both the `blocked` and the
  stale-`active` cases are asserted (`test_unit_update_loop.py:564`, `:573`).
- The Out-of-Scope rule "no counter reset on resume" is enforced by two
  independent suites — mutating it in is killed at unit (M4) and integration
  (M4i) level.
- P2's guards are properly scoped: both placement mutations (M8, M15) died.

**Issues found**: Fixes 1-3 above — one edit site,
`scripts/test_unit_docs_parity.py:377-389`.

**Next steps**: route Fixes 1-3 to an implementer, then re-run the docs-parity
suite plus mutations M11b, M12 and M14. No behavioural change is required and no
shipped prose needs editing.
