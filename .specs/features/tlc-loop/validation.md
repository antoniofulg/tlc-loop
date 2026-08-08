# tlc-loop Validation

**Date**: 2026-08-08
**Round**: **2 of a maximum 3** (round 1 returned FAIL on three ranked gaps; T31/T32/T33 shipped as the fix round)
**Spec**: `.specs/features/tlc-loop/spec.md`
**Diff range**: `12bd8c3..HEAD` (HEAD = `1cc1dd7`, 32 commits). Fix-round surface: `f4e2b30`, `639a202`, `1cc1dd7`.
**Verifier**: independent sub-agent, round 2 — did not write the code, did not write the round-1 report. Coverage re-derived from `spec.md`; the round-1 report's conclusions were treated as claims to re-test, not as findings inherited.
**Scope**: P1 stories only (LOOP-01..LOOP-06). LOOP-07 / T26 is deliberately not delivered and is recorded as such, not as a failure.

---

## Verdict

**Result**: PASS

All three round-1 gaps are closed with discriminating evidence, not merely "a commit was made". The gate is green at **321 passed / 0 failed / 0 skipped**, the sensor killed **16/16** injected faults, and **25/37** P1 acceptance criteria carry a `file:line` assertion whose asserted value matches the spec-defined outcome. The remaining 12 are 11 prose-only criteria (agent-facing instructions, exactly what the approved Test Coverage Matrix specifies for prose) and 1 spec-precision gap that T16 declared correctly and that round 1 independently confirmed.

Five residual observations are recorded at the end. None is an unimplemented `SHALL`, an unevidenced AC, or a regression; they are cheap follow-ups the orchestrator may choose to spend or park.

---

## 1. Are the three round-1 gaps closed?

### Gap 1 — LOOP-01 AC 5: "record the reconciliation in `loop.json`". **CLOSED.**

Round 1's finding was "a field nothing ever writes is not an implementation". Re-derived independently, the whole chain now exists and every link is asserted on value:

| Link | `file:line` | Evidence |
| --- | --- | --- |
| The field exists in the schema | `scripts/_state_io.py:32` (`REQUIRED_KEYS`), `:67` (`"reconciled": []` in `new_state`) | `scripts/test_unit_state_io.py:40` — `self.assertEqual(state["reconciled"], [])` |
| It is type-validated | `scripts/_state_io.py:93` — `for key in ("current_batch", "no_diff_tasks", "reconciled", "iterations")` | `scripts/test_unit_state_io.py:86` — `self.assertIn("reconciled must be a list", str(ctx.exception))` |
| It survives a round trip (durable, not a print) | `scripts/_state_io.py:114-129` | `scripts/test_unit_state_io.py:74-77` — `assertEqual(_state_io.load("demo", root)["reconciled"], [{"task": "T4", "winner": "git", "at": "2026-08-08T00:00:00Z"}])` |
| A writer exists | `scripts/update_loop.py:129-141` (`--reconciled`, registered in `ACTION_FLAGS` at `:63`) | `scripts/test_unit_update_loop.py:254-256` — `assertEqual(entries[0]["task"], "T4")` + `assertEqual(entries[0]["winner"], "git")` + `assertRegex(entries[0]["at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")` |
| Recording is idempotent | `scripts/update_loop.py:134-138` | `scripts/test_unit_update_loop.py:274-276` — after `T4`, `T4,T5`, `T4`: `assertEqual([e["task"] for e in _read(root)["reconciled"]], ["T4", "T5"])` |
| The disagreement is derived | `scripts/detect_phase.py:184` — `reconciled = [task["id"] for task in planned if task["done"] and task["id"] not in done]` | `scripts/test_unit_detect_phase.py:294-298` — `assertEqual(self.line(), "phase=B action=execute_batch batch=P1+P2 tasks=T1,T2,T3,T4,T5,T6 reconciled=T1")` |
| Git still wins (the task is re-dispatched) | `scripts/detect_phase.py:198` | `scripts/test_unit_detect_phase.py:309` — `assertIn("tasks=T1,", self.line())` |
| The tick itself is parsed | `scripts/_tasksmd.py:37` (`DONE_MARK_RE`), `:97` | `scripts/test_unit_tasksmd.py:200` / `:204` — ticked → `assertTrue(...["done"])`, unticked → `assertFalse(...)`; `:224` — a `✅` in the body is **not** a completion claim |

**"Does anything actually call the writer?"** The caller is the orchestrating agent, instructed at `SKILL.md:208-214` inside the Phase B step list, and again at `references/state-schema.md:144-150` and `references/phase-transitions.md:118-125`. There is no script-level caller — and there is no script-level caller for **any** `update_loop.py` flag: `loop.sh` never invokes `update_loop.py` at all (verified by grep over `scripts/loop.sh`, 159 lines, zero hits). `--reconciled` is therefore wired exactly as `--task-done`, `--no-diff`, `--commit`, `--verify-round`, and `--halt` are. It is not weaker than the established pattern. One asymmetry is recorded as Observation 2 below.

**Necessary asymmetry, correctly reasoned.** `detect_phase.py` derives and prints but does not write, because writing would cost it the read-only property that is LOOP-01 AC 6. The split is asserted from both ends: `scripts/test_unit_detect_phase.py:340-345` runs a detect that emits `reconciled=T1` and then asserts the state file bytes, `git status --porcelain`, and `git rev-parse HEAD` are all unchanged.

**Semantics worth naming.** The implementation defines "disagree" one-directionally: a `tasks.md` tick git does not confirm. A trailer with no tick is explicitly not a contradiction, on the reasoning that an unticked header makes no claim (`scripts/_tasksmd.py:7-12`, `references/phase-transitions.md:126-129`). That reading is defensible against the spec's "disagree about a task", it is documented rather than silent, and it is asserted (`scripts/test_unit_detect_phase.py:319-324` — an unticked plan surfaces nothing).

### Gap 2 — LOOP-02 edge case: duplicate `Task:` trailer. **CLOSED, both halves.**

Spec (`spec.md:220`) requires two things: count the task once, and record the ambiguity.

| Half | `file:line` | Assertion |
| --- | --- | --- |
| Counted exactly once | `scripts/_gitio.py:63-68` | `scripts/test_unit_gitio.py:122-124` — `assertEqual(ids.count("T1"), 1)` + `assertEqual(sorted(ids), ["T1","T2"])` + `assertEqual(duplicates, ["T1"])`, over a fixture whose own guard at `:119` asserts `raw.count("T1") == 2` so the duplication is real |
| Named once however many copies | `scripts/_gitio.py:64-65` | `scripts/test_unit_gitio.py:133-134`; `scripts/test_unit_detect_phase.py:389` — `assertTrue(self.line().endswith(" dup=T1"))` after three copies |
| Surfaced, not discarded | `scripts/detect_phase.py:194-195` — `if duplicates: notes.append(f"dup={','.join(duplicates)}")` | `scripts/test_unit_detect_phase.py:372-375` — `assertEqual(self.line(), "phase=B action=execute_batch batch=P1+P2 tasks=T2,T3,T4,T5,T6 dup=T1")` |
| Still counted once *through the detector* | same | `:374` — `T1` is absent from `tasks=`, so the surfaced task is not re-dispatched |
| Rides a non-batch line too | `scripts/detect_phase.py:222`, `:240`, `:242` | `scripts/test_unit_detect_phase.py:402` — `assertEqual(self.line(), "phase=V action=verify round=1 dup=T3")` |
| Clean history says nothing | — | `scripts/test_unit_detect_phase.py:394` — `assertNotIn("dup=", self.line())` |
| Surfacing writes nothing | `scripts/detect_phase.py` (read-only) | `scripts/test_unit_detect_phase.py:415-418` — state bytes, porcelain, and HEAD all unchanged |
| Both advisory fields on one line, fixed order | `scripts/detect_phase.py:63-69` (`_line`) | `scripts/test_unit_detect_phase.py:432-436` — `assertEqual(self.line(), "phase=B action=execute_batch batch=P1+P2 tasks=T2,T3,T4,T5,T6 reconciled=T2 dup=T1")` |

`references/phase-transitions.md:132-137`'s claim that "the duplication is reported rather than dropped" — the sentence round 1 found to be false of the code — is now true of the code. Verified live against this repository: `_gitio.completed_tasks('.')` returns 32 ids, `duplicates == []`, zero empty entries.

### Gap 3 — LOOP-06: halt-reason enumeration parity. **CLOSED, and the check discriminates in both directions.**

Parity holds: `update_loop.HALT_REASONS` (`scripts/update_loop.py:43-52`) lists eight reasons; `SKILL.md:298-299` now names all eight; `references/phase-transitions.md:76-77` already did. Pinned by `scripts/test_unit_docs_parity.py:87-91`.

The prompt asked me to confirm discrimination independently and to check the reverse direction. The file's own self-tests (`:102-118`) pass *synthetic* lists to `assert_parity`, which proves the comparator works but not that the check bites on the real artifacts. I injected both directions into the **real documents and the real constant** in the scratch worktree:

- **Reverse** (a reason documented that the code does not implement): appending `` `cosmic_rays` `` to `SKILL.md:299` → `test_skill_md_enumerates_exactly_the_implemented_reasons` **FAILS**, message names `cosmic_rays`. (Sensor M8.)
- **Forward** (a reason implemented that no document enumerates): adding `"disk_full"` to `update_loop.HALT_REASONS` → **both** parity tests fail, each naming `disk_full`. (Sensor M9.)

Both directions are live against the shipped artifacts, not only against synthetic input.

---

## 2. Did the fix round break or weaken anything?

### `detect_phase.py` must remain side-effect free. **PROVEN, not taken on trust.**

Beyond the in-suite assertions (`scripts/test_unit_detect_phase.py:342-345`, `:415-418`, `:594-597`), I ran an independent whole-tree check in the scratch: a throwaway project seeded so that **both** new fields fire (`T1` ticked but uncommitted → `reconciled=T1`; `T2` committed twice → `dup=T2`), snapshotting every file under the project root — including everything inside `.git` — by SHA-256 content hash, byte size, and `st_mtime_ns`, before and after.

| Scenario | Emitted line | Files added | removed | changed |
| --- | --- | --- | --- | --- |
| `phase=B` with both advisory fields, 3 consecutive runs | `phase=B action=execute_batch batch=P1 tasks=T1 reconciled=T1 dup=T2` (identical all 3 times) | 0 | 0 | **0** |
| `phase=E` path, invoking the **real** sibling `validate_state.py` as a subprocess | `phase=E action=done dup=T1` | 0 | 0 | **0** |

Nothing is written on either path, including the branch that shells out to the sibling validator. The script is also idempotent across repeated runs.

### `_state_io.py` gained a `reconciled` key — did validation loosen? **No: it tightened.**

- `REQUIRED_KEYS` gained an entry (`:32`); nothing was removed. A state file lacking `reconciled` now fails `_validate` at `:82-84`.
- The list-type loop gained `"reconciled"` (`:93`); no existing key left it.
- No status check, dict check, or integer check was relaxed. Diff of `_state_io.py` across the fix round is `+4 / -2`, both deletions being the two lines re-added with the new key appended.
- Sensor M10 removed `"reconciled"` from the type check → `test_a_non_list_reconciled_is_rejected` fails. The tightening is load-bearing.

### Were any pre-existing assertions weakened or removed in the 289 → 321 swap? **No — zero deletions.**

`git diff 0468761..HEAD -- 'scripts/test_*.py'` produces **no removed lines at all**. The fix round is purely additive to the test surface: +407 lines across `test_unit_detect_phase.py` (+168), `test_unit_docs_parity.py` (+122, new file), `test_unit_update_loop.py` (+54), `test_unit_tasksmd.py` (+41), `test_unit_state_io.py` (+22). Test count 289 → 321 (+32). No test was renamed, no assertion made looser, no `skipTest` added.

### The `spec.md` goalposts were not moved by the fix round.

`spec.md` was amended exactly once in the whole diff range, at `1190e47` — **before** round 1 — splitting LOOP-01's old AC 3 into AC 3 (absent → reconstruct) and AC 4 (unparseable → halt), which strengthens the requirement. The reconciliation clause is verbatim identical and merely renumbered to AC 5. No commit in `f4e2b30..HEAD` touches `spec.md`. The fix round closed the gap against unchanged spec text.

---

## 3. Spec-Anchored Acceptance Criteria (re-derived, evidence-or-zero)

Legend: ✅ PASS (assertion targets the spec-defined outcome) · 📄 Prose-only (realized as agent-facing instruction in shipped prose; located, but no executable assertion) · ⚠️ Spec-precision gap · ❌ GAP.

### LOOP-01: Deterministic phase detection and resume

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — exactly one phase line before any work | one line, from the documented vocabulary | `scripts/test_unit_detect_phase.py:197` — `assertEqual(len(lines), 1, f"expected exactly one line, got {lines!r}")` (gate on every `line()` call); `:203` — `assertEqual(self.line(), "phase=0 action=bootstrap")`; `:351` — one line even with three reconciliations | ✅ PASS |
| AC 2 — git trailers authoritative over `loop.json` | git wins over conflicting state | `scripts/test_unit_detect_phase.py:266-268` — `assertEqual(self.line(), "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6")` while state still claims `current_task="T1"`; `scripts/test_unit_gitio.py:91` — `assertEqual(ids, ["T2", "T1"])` | ✅ PASS |
| AC 3 — absent `loop.json` reconstructs | same next task git implies, no failure | `scripts/test_unit_detect_phase.py:225` then `:228` then `:231` — `assertEqual(self.line(), before)` after deletion + re-bootstrap; `scripts/test_int_end_to_end.py:340-348` — same over the real sibling layout | ✅ PASS |
| AC 4 — unparseable `loop.json` halts `state_corrupt` | `phase=H reason=state_corrupt`, no reconstruction | `scripts/test_unit_detect_phase.py:621-623` — `assertTrue(self.line().startswith("phase=H action=halt reason=state_corrupt "))`; `:628` — `assertIn("malformed JSON", line)`; `:648` — `assertNotIn("phase=B", self.line())`; `:634-635` — exit 0, empty stderr | ✅ PASS |
| AC 5 — git is truth **and** the reconciliation is recorded in `loop.json` | git decides; a durable record of the override | git wins: `scripts/test_unit_detect_phase.py:266`, `:309`. Surfaced: `:294-298` — `assertEqual(self.line(), "…tasks=T1,T2,T3,T4,T5,T6 reconciled=T1")`. Recorded on value: `scripts/test_unit_update_loop.py:254-256`. Durable: `scripts/test_unit_state_io.py:74-77`. Idempotent: `scripts/test_unit_update_loop.py:274-276` | ✅ PASS *(was ❌ in round 1)* |
| AC 6 — `loop.json` mutated only through its own script | single writer; detect writes nothing | `scripts/test_unit_detect_phase.py:594-597` — state bytes + porcelain + HEAD unchanged; `:342-345` — same with `reconciled=` active; `:415-418` — same with `dup=` active; `scripts/test_unit_update_loop.py:130` — `assertNotEqual(proc.returncode, 0)` on an objective write | ✅ PASS |

### LOOP-02: Atomic checkpoint per task

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — one atomic commit with `Task:` and `Gate: <level> PASS` | trailers readable back via `%(trailers:key=Task,valueonly)` | `scripts/test_unit_checkpoint.py:201` — `assertEqual(self.commit_count(), before + 1)`; `:206` — `assertEqual(self.trailer("Task"), "T7")`; `:211` — `assertEqual(self.trailer("Gate"), "build PASS")` | ✅ PASS |
| AC 2 — no passing gate, no commit | refusal; commit count unchanged | `scripts/test_unit_checkpoint.py:141-142` (omitted), `:148-149` (`FAIL`), `:155-156` (lowercase `pass`) — each `assertNotEqual(proc.returncode, 0)` + `assertEqual(self.commit_count(), before)`; `:161` — the work is preserved, not discarded | ✅ PASS |
| AC 3 — validate with `check_commit.py`, abort on non-zero | validated **before** staging | `scripts/test_unit_checkpoint.py:171-172` — refusal + no commit; `:177` — `assertEqual(self.staged(), [])`; `:184` — `assertEqual(fh.read(), GOOD_MESSAGE)` (the payload handed over is asserted, not merely that the call happened) | ✅ PASS |
| AC 4 — at most one commit per task, never batched | one commit; a repeated `Task:` refused or deduped | `scripts/test_unit_checkpoint.py:201`; `:242` / `:247` — a message already carrying the trailers yields exactly one of each; `:256-257` — `assertEqual(ids, ["T7"])` + `assertEqual(duplicates, [])`; `:263-264`, `:270-271` — a contradicting trailer is refused | ✅ PASS |
| AC 5 — executor forbidden from committing; the loop checkpoints | prohibition + ownership | `references/executors.md:20`; `SKILL.md:57-60`; `references/checklist.md:58-60`, `:74-76`. Orchestrator-side checkpointing exercised at `scripts/test_int_end_to_end.py:236-251`, but the prohibition itself carries no executable assertion | 📄 Prose-only |
| AC 6 — no file changes → record completion, no fabricated diff | `SKIP: no changes`, exit 0, no commit | `scripts/test_unit_checkpoint.py:279` — `assertIn("SKIP: no changes", proc.stdout)`; `:282` — `assertEqual(self.checkpoint().returncode, 0)`; `:287` — `assertEqual(self.commit_count(), before)`; `scripts/test_unit_update_loop.py:219` — `assertEqual(_read(root)["no_diff_tasks"], ["T4"])` | ✅ PASS |

**Edge case (spec.md:220) — duplicated `Task:` trailer**: see Gap 2 above. ✅ both halves.

### LOOP-03: Self-healing repair loop

Entirely agent-facing prose. The approved Test Coverage Matrix (`tasks.md:26`) assigns prose "none — build gate only", so this is by design; under evidence-or-zero none of the five carries an executable assertion.

| Criterion | Spec-defined outcome | `file:line` | Result |
| --- | --- | --- | --- |
| AC 1 — failure keeps the phase open, no final state written | phase stays open | `references/recovery-loop.md:14`, `:87`; `references/checklist.md:20-24` | 📄 Prose-only |
| AC 2 — diagnose root cause; no unchanged retry | a blind rerun is not a repair | `references/recovery-loop.md:27`, `:34` | 📄 Prose-only |
| AC 3 — never weaken/delete/skip a test to pass a gate | explicit prohibition | `references/recovery-loop.md:54-55`; `references/checklist.md:113-115` | 📄 Prose-only |
| AC 4 — repair and continue rather than report a blocker | repairable ≠ blocker | `references/recovery-loop.md:87-97` | 📄 Prose-only |
| AC 5 — three-criteria external blocker → record, halt, no signature | evidence + halt, no done-signature | `references/recovery-loop.md:131-171`; `SKILL.md:315` | 📄 Prose-only |

### LOOP-04: Independent verification with bounded fix loop

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — fresh verifier dispatched, no prompting | author ≠ verifier | `SKILL.md:233-234`; `references/executors.md:133-134`; `references/checklist.md:80-84` | 📄 Prose-only |
| AC 2 — verifier read-only over the real tree | no code/test modification | `SKILL.md:236`; `references/checklist.md:85-87` | 📄 Prose-only |
| AC 3 — FAIL routes gaps to `fix`, then re-dispatches verify | `phase=F` on FAIL+open gaps; back to `phase=V` when gaps close | `scripts/test_unit_detect_phase.py:460` — `assertEqual(self.line(), "phase=F action=fix round=1")`; `:453` — `assertEqual(self.line(), "phase=V action=verify round=2")` with gaps 0; `:536` — a FAIL report still yields `phase=F` | ✅ PASS |
| AC 4 — verify-round limit reached without PASS → halt and escalate | `phase=H reason=verify_exhausted`, checked ahead of V and F | `scripts/test_unit_detect_phase.py:484-486` — `assertTrue(line.startswith("phase=H action=halt reason=verify_exhausted "))`; `:501-502` — `assertNotIn("phase=F", line)` + `assertIn("reason=verify_exhausted", line)`; `:506` — omitted `max_rounds` never halts (`round=100`); `:522` — pending work still dispatches at the ceiling | ✅ PASS |
| AC 5 — PASS confirmed with `validate_state.py`; non-zero = not done | `phase=E` only on exit 0 | `scripts/test_unit_detect_phase.py:530` — `assertEqual(self.line(), "phase=E action=done")`; `:536` — FAIL report → `phase=F`; `scripts/test_int_end_to_end.py:397` — `assertEqual(self.detect(), "phase=E action=done")` against the **real** sibling validator | ✅ PASS |

### LOOP-05: Per-stage provider, model, and effort

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — resolve provider/model/effort and translate through the adapter table | per-provider command line | `scripts/test_unit_resolve_stage.py:76-77` — `assertIn("codex exec -m gpt-5.6-luna", line)` + `assertIn("-c model_reasoning_effort=max", line)`; `:93` — `assertIn("claude-opus-5[effort=high]", line)`; `:125-126` — `assertIn("--model opus", line)` + `assertIn("--effort high", line)` | ✅ PASS |
| AC 2 — unsupported effort rejected before dispatch | rejection names stage, provider, accepted values | `scripts/test_unit_config.py:165-166` — `assertIn("stages.verify", message)` + `assertIn("ultra", message)` (the reachable path); `scripts/test_unit_resolve_stage.py:180-181` — `check_effort("claude","minimal","implement")` raises naming both; `:193-196` — `ultra` rejected for all three providers | ⚠️ Spec-precision gap (see note) |
| AC 3 — provider == running harness → native sub-agent | `kind=agent`, no CLI | `scripts/test_unit_resolve_stage.py:142` — `assertEqual(line, "kind=agent provider=claude model=opus effort=high")`; `:147` — `assertNotIn("cmd=", line)` | ✅ PASS |
| AC 4 — config read-only; runtime values recorded in `loop.json` | no write to `loop.config.toml` | `scripts/_config.py` exposes no writer (`load_config` only); `scripts/test_unit_init_loop.py:216` — `assertEqual(self.state()["harness_resolved"], "cursor")`; `scripts/test_int_end_to_end.py:324` — `assertEqual(self.state_bytes(), before)` | ✅ PASS |
| AC 5 — launch/auth/quota failure halts with the reason recorded | `phase=H reason=executor`, resumable | `scripts/test_unit_update_loop.py:330-331` — `assertEqual(halt["reason"], "executor")` + `assertEqual(halt["detail"], "codex quota exhausted")`; `scripts/test_unit_detect_phase.py:550` — `assertIn("reason=executor", self.line())`. The trigger conditions are prose (`references/executors.md:203-206`) | ✅ PASS (recording and printing asserted) |
| AC 6 — verify an executor's evidence before advancing | a claim without an artifact is not completion | `references/executors.md:61-71`, `:174-180`; `references/checklist.md:61-65` | 📄 Prose-only |

**⚠️ AC 2 note — independently re-confirmed.** `_config.EFFORTS` (`scripts/_config.py:21`) rejects any value outside `low/medium/high/xhigh/max` at load time; `resolve_stage.PROVIDER_EFFORTS` gives `claude` and `cursor` exactly that set and `codex` a superset, and `check_effort` returns early for any provider absent from the table. No config-legal effort can therefore reach the per-provider rejection, so the branch is asserted directly on `check_effort` rather than end to end. `tasks.md` declares this accurately. Unchanged from round 1; the fix round did not touch this path.

### LOOP-06: Unattended continuation and stop conditions

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — re-enter detection in the same turn | control is not returned while non-terminal | `SKILL.md:326` (in-turn gate, prose); `references/checklist.md:34-36`. Cross-turn analogue asserted: `scripts/test_int_loop_sh.py:177-178` — `assertEqual(self.spawns(), 4)` + `assertEqual(self.detect_calls(), 5)` over `0→B→V→F→E` | 📄 Prose-only (in-turn); ✅ for the driver |
| AC 2 — print the literal done-signature when `validate_state.py` exits 0 | `__TLC_LOOP__ feature=<feature> verify=PASS` | `SKILL.md:286-289`; parity across `references/checklist.md:131-132`, `assets/iteration-summary.template.md:36`, `assets/goal-condition.template.md:11`. `detect_phase` prints `phase=E action=done` (`scripts/test_unit_detect_phase.py:530`); the agent prints the signature. No assertion on the signature string itself | 📄 Prose-only |
| AC 3 — resolve continuation from the harness, record it | `harness_resolved` in `loop.json` | `scripts/test_unit_init_loop.py:212` — `assertEqual(self.state()["harness_resolved"], "claude")`; `:216` — `"cursor"`; `:242`, `:252` — explicit/configured `--respawn` records `"codex"` | ✅ PASS |
| AC 4 — inconclusive detection halts and asks | non-zero exit, no state written, tells the user how | `scripts/test_unit_init_loop.py:224` — `assertNotEqual(proc.returncode, 0)`; `:228` — `assertIn("--respawn", proc.stderr)`; `:232` — `assertFalse(os.path.exists(self.state_path()))`; `:236-237` — two markers at once are also inconclusive, still no state file | ✅ PASS |
| AC 5 — objective immutable for the run | verbatim at bootstrap, unwritable after | `scripts/test_unit_init_loop.py:200` — `assertEqual(self.state()["objective"], odd)` (punctuation and spacing preserved); `scripts/test_unit_update_loop.py:142` — unchanged after a rejected write; `:148` — `assertEqual(_read(root)["iteration"], 0)`, so a rejected call applies none of its other flags | ✅ PASS |
| AC 6 — no new commit across N iterations → halt | `reason=no_progress` | `scripts/test_unit_detect_phase.py:555` — `assertIn("reason=no_progress", self.line())`; `scripts/test_unit_update_loop.py:182-184` — counter 1→2; `:193` — reset to 0 on a recorded commit; `scripts/test_int_end_to_end.py:372` — `assertTrue(line.startswith("phase=H action=halt reason=no_progress "))` | ✅ PASS |
| AC 7 — same task's gate fails more than N attempts → halt | `reason=gate_stuck`, task named | `scripts/test_unit_detect_phase.py:561-562` — `assertIn("reason=gate_stuck", line)` + `assertIn("T4", line)`; `scripts/test_unit_update_loop.py:172` — `assertEqual(..., {"T3": 2, "T4": 1})` | ✅ PASS |
| AC 8 — `max_iterations` / `max_minutes` reached → write state and halt cleanly | `reason=limit` | `scripts/test_unit_detect_phase.py:567` — `assertIn("reason=limit", self.line())`; `:580` — `assertTrue(self.line().startswith("phase=B "))` when the limit is omitted | ✅ PASS |
| AC 9 — remote/destructive operation → halt and wait for authorization | `reason=blast_radius`, no proceeding | `scripts/test_unit_detect_phase.py:543-544` — `assertTrue(line.startswith("phase=H action=halt reason=blast_radius "))` + `assertIn('detail="push required"', line)`. The wait discipline is prose: `SKILL.md:70-77`, `references/checklist.md:143-145` | ✅ PASS (halt asserted); 📄 for the wait discipline |

### Count (re-derived independently — not copied from round 1)

**37 P1 criteria** (LOOP-01: 6, LOOP-02: 6, LOOP-03: 5, LOOP-04: 5, LOOP-05: 6, LOOP-06: 9).

| Result | Count | Where |
| --- | --- | --- |
| ✅ PASS with a spec-matched assertion | **25** | LOOP-01 ×6, LOOP-02 ×5, LOOP-04 ×3, LOOP-05 ×4, LOOP-06 ×7 |
| 📄 Prose-only (located, no executable assertion) | **11** | LOOP-02 AC 5; LOOP-03 ×5; LOOP-04 AC 1–2; LOOP-05 AC 6; LOOP-06 AC 1–2 |
| ⚠️ Spec-precision gap (declared) | **1** | LOOP-05 AC 2 |
| ❌ GAP | **0** | — |

Round 1 reported 24 matched / 12 prose-only / 1 gap. The delta is exactly the one gap closing (LOOP-01 AC 5 moving from ❌ to ✅); my prose-only count of 11 differs from round 1's 12 because round 1 split LOOP-01 AC 5 into two rows and counted 38 lines against 37 criteria.

### P2: LOOP-07 — Handoff from tlc-spec-driven

**Not delivered.** T26 edits a skill outside this repository and awaits the user's go-ahead. Recorded as not-delivered, not as a failure. No verdict rendered.

---

## Edge Cases (spec.md:218-226)

| Edge case | Evidence | Handled? |
| --- | --- | --- |
| Not a git repository → halt at bootstrap | `scripts/test_unit_init_loop.py:142-143` — `assertNotEqual(proc.returncode, 0)` + `assertIn("git", proc.stderr.lower())` | ✅ |
| `tasks.md` missing or fails `validate_tasks.py` → refuse, report errors | `scripts/test_unit_init_loop.py:148-149`, `:154-155` — `assertIn("validate_tasks", proc.stderr)`; `:166` — no state written | ✅ |
| Duplicated `Task:` trailer → completed once **and record the ambiguity** | Counted once: `scripts/test_unit_gitio.py:122-124`. Surfaced: `scripts/test_unit_detect_phase.py:372-375`, `:389`, `:402`, `:432-436` | ✅ *(was ⚠️ half-handled in round 1)* |
| Uncommitted changes mapping to no task → halt and ask | `references/recovery-loop.md:96`, `:149` (prose; no worktree check in `detect_phase.py`) | 📄 Prose-only |
| Executor commits despite the ban → keep phase open, preserve work | `references/executors.md:20-30`; `references/checklist.md:74-76` (prose) | 📄 Prose-only |
| Batch worker reports a task failure → do not start the next batch | `SKILL.md:225`; `references/recovery-loop.md` (prose) | 📄 Prose-only |
| `.specs/loop.config.toml` absent → run on documented defaults | `scripts/test_unit_config.py:32-47` — the whole default tree asserted key by key; `:69-73` — every limit `None`; `scripts/test_unit_init_loop.py:187` — bootstrap succeeds with no config | ✅ |
| Configured provider CLI not installed → halt with the missing command named | `references/executors.md:205-206` (prose). No `shutil.which` check in `resolve_stage.py`; `loop.sh:157-158` surfaces the non-zero exit but does not name it as a missing command | 📄 Prose-only |

---

## Discrimination Sensor

**Isolation**: a temporary `git worktree` created from `HEAD` (`1cc1dd7`) under the session scratchpad. Every mutation was applied to the worktree copy, tested there, then reverted with `git checkout -- <file>`. The worktree was removed with `git worktree remove --force` and pruned. **No `git stash` at any point.** Pre-sensor baseline of the real tree: `git status --porcelain` empty, `HEAD = 1cc1dd7`.

**Depth**: expanded — **16 mutations**, weighted to the fix round's new code (M1–M10, M14: `reconciled` persistence, `dup=` surfacing, the parity test, the `_state_io` schema change) and to the highest-consequence existing paths (M11 `checkpoint.py`, M12 `_gitio.completed_tasks`, M13/M15/M16 `detect_phase.py`).

| # | File | Mutation | Killed? |
| --- | --- | --- | --- |
| M1 | `scripts/detect_phase.py:184` | Dropped the `and task["id"] not in done` guard — a tick git **does** confirm is reported as a disagreement | ✅ Killed (2 failures) |
| M2 | `scripts/detect_phase.py:185-186` | `reconciled=` never surfaced (reverts T31's detect half) | ✅ Killed (4) |
| M3 | `scripts/_tasksmd.py:97` | Return-value fault: every task header parses as ticked (`"done": True`) | ✅ Killed (17) |
| M4 | `scripts/update_loop.py:136-137` | Reconciliation record loses idempotence — the same disagreement appended every iteration | ✅ Killed (1) |
| M5 | `scripts/update_loop.py:140` | Payload fault: the record names `winner: "tasks.md"` instead of `"git"` | ✅ Killed (1) |
| M6 | `scripts/detect_phase.py:194-195` | `dup=` never surfaced — reverts T32, i.e. reinstates the round-1 gap | ✅ Killed (6) |
| M7 | `scripts/_gitio.py:64-65` | A thrice-duplicated trailer is named once per extra copy instead of once | ✅ Killed (2) |
| M8 | `SKILL.md:299` | **Reverse parity direction**: the document enumerates `cosmic_rays`, which the code does not implement | ✅ Killed (1) |
| M9 | `scripts/update_loop.py:51` | **Forward parity direction**: the code gains `disk_full`, which no document enumerates | ✅ Killed (2 — both documents) |
| M10 | `scripts/_state_io.py:93` | Schema loosening: `reconciled` is no longer type-checked as a list | ✅ Killed (1) |
| M11 | `scripts/checkpoint.py:112` | Gate assertion flipped — commits even when the gate did not pass | ✅ Killed (4) |
| M12 | `scripts/_gitio.py:50` | `completed_tasks` loses `--reverse` — first-seen order becomes newest-first | ✅ Killed (1) |
| M13 | `scripts/detect_phase.py:233` | Off-by-one on the verify ceiling (`>=` → `>`) — the halt fires one round late | ✅ Killed (3) |
| M14 | `scripts/detect_phase.py:207` | `phase=B` drops all advisory fields while other lines keep them | ✅ Killed (8) |
| M15 | `scripts/detect_phase.py:166` | Git trailers ignored — completion no longer derives from git | ✅ Killed (22) |
| M16 | `scripts/detect_phase.py:222` | `phase=E action=done` replaced with a bogus batch line | ✅ Killed (2) |

**Result**: **16/16 killed, 0 survived** — ✅

**Isolation check (post-sensor)**: `git worktree list` → only `/Users/antoniofulg/Projects/tlc-loop  1cc1dd7 [main]`. `git status --porcelain` → empty, byte-identical to the pre-sensor baseline. `git rev-parse HEAD` → `1cc1dd7`. Real tree never mutated.

---

## Independent Check of the Fix Round's Self-Declared Claim

> "T31, T32, T33 each expanded their `Where` beyond the single file named in `tasks.md`, and each `Where` was updated to match."

**CONFIRMED on both counts — and the expansions are necessary, not convenient.**

| Task | Declared `Where` (current `tasks.md`) | Non-test files the commit actually touched | Match? |
| --- | --- | --- | --- |
| T31 (`f4e2b30`) | `update_loop.py`, `_state_io.py`, `_tasksmd.py`, `detect_phase.py`, `state-schema.md`, `phase-transitions.md`, `SKILL.md` (`tasks.md:1078`) | exactly those 7 | ✅ exact |
| T32 (`639a202`) | `detect_phase.py`, `phase-transitions.md` (`tasks.md:1107`) | exactly those 2 | ✅ exact |
| T33 (`1cc1dd7`) | `test_unit_docs_parity.py`, `SKILL.md` (`tasks.md:1132`) | exactly those 2 | ✅ exact |

Test files are not listed in any `Where` anywhere in this plan; they are carried by the `Tests: unit` field, so their omission is the house convention rather than an undeclared touch. (T33 is the exception that lists its test file, because the test *is* the deliverable.)

**Necessity, file by file for T31** — the only expansion large enough to question:

- `update_loop.py` — mandatory. LOOP-01 AC 6 makes it the sole writer of `loop.json`.
- `_state_io.py` — mandatory. It is the only module that touches `loop.json`; a field it does not know about cannot round-trip and would fail `_validate`.
- `_tasksmd.py` — mandatory. It is the only reader of `tasks.md`; the disagreement cannot be detected without reading the tick, and `tasks.md` has no status field, so the tick had to be introduced as a parsed attribute.
- `detect_phase.py` — mandatory *given the constraint*. The disagreement is only knowable where git and the plan meet, which is the detector. Since the detector must stay read-only (LOOP-01 AC 6, asserted at `scripts/test_unit_detect_phase.py:342-345`), it can only surface, and the writer must be a separate call. The alternative — letting the detector write — would trade one AC for another.
- `references/state-schema.md`, `references/phase-transitions.md`, `SKILL.md` — mandatory for a skill whose shipped artifact is prose. A field an agent is never told to record is a field that never gets recorded. `state-schema.md` was also an explicit Done-when item.

The `Where` expansion is a consequence of the single-writer and read-only invariants, not of convenience. The declared-scope note at `tasks.md:1093` states the same reasoning and is accurate.

**T33's red-then-green claim** (`tasks.md:1143`) is independently corroborated: sensor M8 and M9 reproduce failures in both directions against the real artifacts, and M8's failure message is the same shape the note quotes.

---

## Payload / Conjunction Rule

Checked for every named field in a returned object or written file. No instance of "the call ran" standing in for "the value is right":

- `update_loop.py --reconciled` — all three fields of the entry asserted: `task` (`test_unit_update_loop.py:254`), `winner` (`:255`), `at` by shape (`:256`). Not merely "an entry exists".
- `_state_io` — the whole initial shape asserted field by field (`test_unit_state_io.py:32-49`), including `reconciled == []` (`:40`) and the deliberate absence of `completed_tasks` (`:54`).
- `detect_phase.py` — the **complete line** is compared, not a substring, wherever the shape is deterministic (`test_unit_detect_phase.py:294-298`, `:372-375`, `:402`, `:432-436`). Advisory-field ordering is pinned as part of the whole-line comparison.
- `checkpoint.py` — trailer values are read back out of git (`:206`, `:211`), the message handed to `check_commit.py` is compared byte for byte (`:184`), and the committed file list is asserted (`:297`, `:303`, `:310`, `:340`).
- `_gitio.completed_tasks` — both tuple elements asserted, including `duplicates == []` on the happy path (`test_unit_checkpoint.py:257`).
- `test_unit_docs_parity.assert_parity` — the failure **message** is asserted to name the offending reason and to *not* name innocent ones (`:106-107`), so a blanket "sets differ" error would fail the test.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ stdlib only; no dependency added; the fix round is +87 non-test lines total |
| Surgical changes | ✅ each fix commit touches only its declared `Where` + its tests + `tasks.md`; the round-1 finding (T29's undeclared 12-file expansion) has been addressed by the declared-scope convention now used by T31 |
| No scope creep | ✅ nothing beyond the three ranked gaps; out-of-scope items in `spec.md:28-37` respected |
| Matches patterns | ✅ `--reconciled` mirrors `--no-diff` exactly (flag → `ACTION_FLAGS` → keyed append in `apply`); the advisory-field mechanism reuses one `_line` helper |
| Spec-anchored outcome check | ✅ for all 25 code-realizable ACs; the 1 precision gap is flagged, not silently passed |
| Per-layer Coverage Expectation met | ✅ support modules and CLI entrypoints have per-branch tests; prose is build-gate only per the approved matrix (`tasks.md:26`) — and `test_unit_docs_parity.py` now adds coverage **above** the matrix for one prose invariant |
| Every test maps to a spec requirement | ✅ every new class carries a docstring naming its task and AC (`Reconciliation` → T31/LOOP-01 AC 5, `DuplicateTrailer` → T32/LOOP-02 edge case, `HaltReasonParity` → T33/LOOP-06); no unclaimed tests |
| Documented guidelines followed | ✅ none exist — strong defaults applied (stdlib `unittest`, tmpdir-scoped, zero dependencies), as recorded in `tasks.md:18` |
| Hook bypass | ✅ `--no-verify` absent from `checkpoint.py`, asserted at `test_unit_checkpoint.py:394` |
| No assertion weakened or test removed | ✅ zero deleted lines in `scripts/test_*.py` across `0468761..HEAD` |

---

## Gate Check

- **Gate command** (Build, from `tasks.md:36`): `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Result**: **321 passed, 0 failed, 0 skipped** (31.5s, exit 0)
- **Test count before the fix round**: 289
- **Test count after the fix round**: 321
- **Delta**: **+32** tests, +407 test lines, **−0** lines removed
- **Test count before the feature**: 0 — `12bd8c3` is the planning-docs commit of a greenfield repository
- **Skipped tests**: none. `test_int_tlc_validators` and `test_int_end_to_end` skip only when the sibling skill is absent; it is installed at `~/.agents/skills/tlc-spec-driven/`, so both ran against the real validators.
- **Failures**: none. `compileall` and `bash -n scripts/loop.sh` both clean.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1–T13 | ✅ Done | Foundation, detection, state mutation, checkpoint, bootstrap |
| T14 | ⚠️ Partial | codex environment marker UNRESOLVED — recorded as unresolved rather than guessed; `init_loop.HARNESS_MARKERS` carries no codex entry. Deviation declared in `tasks.md`. Unchanged from round 1 |
| T15–T25 | ✅ Done | Providers, executors, recovery, driver, skill assembly, validator mutation tests |
| T26 | ⛔ Not delivered | LOOP-07 / P2. Edits a skill outside this repo; awaiting user go-ahead. Out of scope for this verdict |
| T27–T30 | ✅ Done | End-to-end, corrupt-state halt, verify ceiling, loop-state ignore |
| T31 | ✅ Done | `f4e2b30` — reconciliation recorded; closes round-1 Gap 1 |
| T32 | ✅ Done | `639a202` — duplicate trailer surfaced; closes round-1 Gap 2 |
| T33 | ✅ Done | `1cc1dd7` — halt-enum parity pinned as a test; closes round-1 Gap 3 |

Verified live against this repository: `_gitio.completed_tasks('.')` returns **32 unique ids** (T1–T25, T27–T33) with **zero duplicates and zero empty entries**; `_tasksmd.parse` finds 33 planned tasks, 32 ticked, and the only pending task is **T26**. `reconciled` computes to `[]` — the plan and git agree.

---

## Residual Observations (not gaps; no AC is unmet)

1. **`dup=` is reachable only through a linked reference, and is never recorded durably.** `SKILL.md` never mentions the field; the agent learns it exists by following `SKILL.md:143-144` into `references/phase-transitions.md:74-77`. Unlike `reconciled`, there is no `loop.json` field, no `update_loop.py` flag, no `references/checklist.md` box, and no slot in `assets/iteration-summary.template.md`. The spec says "record the ambiguity", and the ambiguity is in the transcript on the phase line, which satisfies the letter — but it is a weaker close than T31's, and an emitted field the entrypoint never names risks being ignored. *Cheapest fix: one line in the Phase B step list and one checklist box.*
2. **`--reconciled` has no `references/checklist.md` box.** The Phase B self-audit gates `--no-diff` explicitly (`checklist.md:68-71`, with `no_diff_tasks` named as the evidence) but has no equivalent for `--reconciled`. The audit designed to catch a skipped record is the one place that would notice the agent forgetting, and it does not look.
3. **`loop.sh` parsing of advisory-bearing terminal lines is new behavior with no test.** T32 made it possible for `phase=E` and `phase=V` to carry a trailing field for the first time. I verified empirically that `loop.sh:123-126` still extracts the phase letter correctly (`phase=E action=done dup=T1` → exit 0; `phase=B … reconciled=T1 dup=T2` → treated as non-terminal), but `scripts/test_int_loop_sh.py` stubs only ever emit bare lines, so nothing pins it.
4. **Undocumented migration effect of the `_state_io` schema change.** A `loop.json` written before `f4e2b30` lacks `reconciled` and now fails `_validate`, so a run in flight across that commit halts with `phase=H reason=state_corrupt` and needs a re-bootstrap. That is the correct and documented answer for a state file the codec did not write (LOOP-01 AC 4), and `loop.json` is gitignored machine state, so the blast radius is one lost counter set. No document mentions it.
5. **`spec.md`'s Requirement Traceability table is stale.** `spec.md:235-241` still reads Phase `Design` / Status `Pending` for LOOP-01..LOOP-07. This Verifier is read-only on the real tree; the update belongs to the orchestrator. Proposed new statuses are in the table below.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| LOOP-01 | Pending | ✅ Verified (all 6 ACs asserted; AC 5 closed this round) |
| LOOP-02 | Pending | ✅ Verified (AC 5 prose-only; the duplicate-trailer edge case closed this round) |
| LOOP-03 | Pending | ⚠️ Documented only — no executable evidence, by the approved coverage matrix |
| LOOP-04 | Pending | ✅ Verified (AC 1–2 prose-only) |
| LOOP-05 | Pending | ✅ Verified (AC 2 spec-precision gap, correctly declared; AC 6 prose-only) |
| LOOP-06 | Pending | ✅ Verified (AC 1–2 prose-only; halt-enum parity now gated by a test) |
| LOOP-07 | Pending | ⛔ Not delivered (P2, out of scope, awaiting user authorization) |

---

## Summary

**Overall**: ✅ Ready

**Round 1 gaps**: 3/3 closed, each with a `file:line` assertion on the spec-defined value and a mutation that proves the assertion bites.
**Spec-anchored check**: 25/37 P1 ACs matched the spec-defined outcome with a `file:line` assertion · 11 prose-only · 1 spec-precision gap (declared) · **0 gaps**
**Sensor**: 16/16 mutations killed, 0 survived
**Gate**: 321 passed, 0 failed, 0 skipped

**What works**: Phase detection is derived rather than stored, and is now provably inert — a whole-tree content-and-mtime snapshot across `phase=B` (with both advisory fields firing) and `phase=E` (invoking the real sibling validator) shows zero files added, removed, or changed. The reconciliation record is a complete chain: parsed from `tasks.md`, derived where git and the plan meet, printed by the read-only detector, written by the single writer, type-checked by the codec, durable across a round trip, and idempotent — every link asserted on value, every link killed by a mutation. The duplicate-trailer ambiguity is now reported rather than dropped, on any non-halt line, once per task however many copies exist, and the shipped sentence that previously lied about it is now true. The halt vocabulary is gated by a test that fails in **both** directions against the real documents, which is the specific failure mode — a one-time manual check going stale — that produced round-1 Gap 3.

**Issues found**: none blocking. Five residual observations recorded above, ranked; the top two (`dup=` not named in `SKILL.md`; `--reconciled` absent from the self-audit checklist) are single-line documentation additions.

**Next steps**: Mark the P1 group verified and update the traceability table in `spec.md`. Optionally spend one cheap documentation task on Observations 1–2 and one test on Observation 3. LOOP-07 / T26 stays parked until the user authorizes editing the sibling skill.
