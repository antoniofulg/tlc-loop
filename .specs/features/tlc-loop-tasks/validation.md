# tlc-loop-tasks Validation

**Date**: 2026-08-08
**Spec**: `.specs/features/tlc-loop-tasks/spec.md`
**Diff range**: `12bd8c3..HEAD` (HEAD = `0468761`, 29 commits)
**Verifier**: independent sub-agent (author ≠ verifier); re-derived from `spec.md`, not from `design.md` or code comments
**Scope**: P1 stories only (LOOP-01..LOOP-06). LOOP-07 / T26 is deliberately not delivered and is recorded as such, not as a failure.

---

## Verdict

**FAIL** — on three grounded, low-severity gaps. Everything the gate and the sensor can reach is sound: 289/289 tests pass, 18/18 injected faults were killed, and every code-realizable P1 criterion has a `file:line` assertion whose asserted value matches the spec-defined outcome. The three gaps are two undelivered `SHALL record` clauses and one stale enumeration in the shipped entrypoint.

**Result**: FAIL

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1–T13 | ✅ Done | Foundation, detection, state mutation, checkpoint, bootstrap |
| T14 | ⚠️ Partial | codex environment marker UNRESOLVED; recorded as unresolved rather than guessed, `init_loop.HARNESS_MARKERS` carries no codex entry. Deviation is declared in `tasks.md:488-494`. |
| T15–T25 | ✅ Done | Providers, executors, recovery, driver, skill assembly, validator mutation tests |
| T26 | ⛔ Not delivered | LOOP-07 / P2. Edits a skill outside this repo; awaiting user go-ahead. Out of scope for this verdict. |
| T27–T30 | ✅ Done | End-to-end, corrupt-state halt, verify ceiling, loop-state ignore |

`_gitio.completed_tasks('.')` over the real repository returns 29 unique ids (T1–T25, T27–T30) with **zero duplicates and zero empty entries**, confirming the trailer record is intact.

---

## Spec-Anchored Acceptance Criteria

Legend: ✅ PASS (assertion targets the spec-defined outcome) · 📄 Prose-only (realized as agent-facing instructions in the shipped skill; located, but no executable assertion) · ❌ GAP · ⚠️ Spec-precision gap.

### LOOP-01: Deterministic phase detection and resume

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — exactly one phase line before any work | one line, from the documented vocabulary | `scripts/test_unit_detect_phase.py:197` — `self.assertEqual(len(lines), 1, f"expected exactly one line, got {lines!r}")`; `:203` — `self.assertEqual(self.line(), "phase=0 action=bootstrap")` | ✅ PASS |
| AC 2 — git trailers authoritative over `loop.json` | git wins over conflicting state | `scripts/test_unit_detect_phase.py:266` — `self.assertEqual(self.line(), "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6")` (state still claims T1 in flight); `scripts/test_unit_gitio.py:91` — `self.assertEqual(ids, ["T2", "T1"])` | ✅ PASS |
| AC 3 — absent `loop.json` reconstructs | same next task git implies, no failure | `scripts/test_unit_detect_phase.py:228` — `self.assertEqual(self.line(), "phase=0 action=bootstrap")` then `:231` — `self.assertEqual(self.line(), before)`; `scripts/test_int_end_to_end.py:348` — `self.assertEqual(self.detect(), before)` | ✅ PASS |
| AC 4 — unparseable `loop.json` halts `state_corrupt` | `phase=H reason=state_corrupt`, no reconstruction | `scripts/test_unit_detect_phase.py:453` — `self.assertTrue(self.line().startswith("phase=H action=halt reason=state_corrupt "), self.line())`; `:480` — `self.assertNotIn("phase=B", self.line())`; `:460` — `self.assertIn("malformed JSON", line)` | ✅ PASS |
| AC 5a — `tasks.md` vs git disagree → git is truth | git decides | `scripts/test_unit_detect_phase.py:266` (above); `scripts/test_unit_detect_phase.py:259` — `self.assertEqual(self.line(), "phase=B action=execute_batch batch=P2 tasks=T5,T6")` (`no_diff_tasks` union) | ✅ PASS |
| AC 5b — **record the reconciliation in `loop.json`** | a durable record of the disagreement | **no evidence.** Searched `scripts/*.py`, `SKILL.md`, `references/` for `reconcil` — the only hit is `design.md:409`. `_state_io.REQUIRED_KEYS` has no such field; `update_loop.py` has no flag; `detect_phase.py` is read-only by design and writes nothing. | ❌ GAP |
| AC 6 — `loop.json` mutated only through its own script | single writer; detect writes nothing | `scripts/test_unit_detect_phase.py:427` — `self.assertEqual(fh.read(), state_before)` + `:428-429` porcelain and HEAD unchanged; `scripts/test_int_end_to_end.py:324` — `self.assertEqual(self.state_bytes(), before)`; `scripts/test_unit_update_loop.py:130` — `self.assertNotEqual(proc.returncode, 0)` (objective write rejected) | ✅ PASS |

### LOOP-02: Atomic checkpoint per task

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — one atomic commit with `Task:` and `Gate: <level> PASS` | trailers readable back via `%(trailers:key=Task,valueonly)` | `scripts/test_unit_checkpoint.py:206` — `self.assertEqual(self.trailer("Task"), "T7")`; `:211` — `self.assertEqual(self.trailer("Gate"), "build PASS")`; `:201` — `self.assertEqual(self.commit_count(), before + 1)` | ✅ PASS |
| AC 2 — no passing gate, no commit | refusal, commit count unchanged | `scripts/test_unit_checkpoint.py:141-142` — `assertNotEqual(proc.returncode, 0)` + `assertEqual(self.commit_count(), before)` (omitted); `:148-149` (`FAIL`); `:155-156` (lowercase `pass`) | ✅ PASS |
| AC 3 — validate with `check_commit.py`, abort on non-zero | validated **before** staging | `scripts/test_unit_checkpoint.py:171-172` — refusal + no commit; `:177` — `self.assertEqual(self.staged(), [])`; `:184` — `self.assertEqual(fh.read(), GOOD_MESSAGE)` (payload asserted, not just that the call ran) | ✅ PASS |
| AC 4 — at most one commit per task, never batched | one commit; a repeated `Task:` is refused/deduped | `scripts/test_unit_checkpoint.py:201` (exactly one); `:242` — `self.assertEqual(self.trailer("Task"), "T7")` with a message already carrying the trailer; `:256-257` — `assertEqual(ids, ["T7"])` / `assertEqual(duplicates, [])`; `:264` — contradicting trailer refused | ✅ PASS |
| AC 5 — executor forbidden from committing; the loop checkpoints | prohibition + ownership | `references/executors.md:20` "### 1. An executor never commits"; `SKILL.md:57-60` "Two single writers, no exceptions"; `scripts/test_int_end_to_end.py:236-251` exercises orchestrator-side checkpointing. No assertion of the prohibition itself. | 📄 Prose-only |
| AC 6 — no file changes → record completion, no fabricated diff | `SKIP: no changes`, exit 0, no commit | `scripts/test_unit_checkpoint.py:279` — `self.assertIn("SKIP: no changes", proc.stdout)`; `:282` — `assertEqual(self.checkpoint().returncode, 0)`; `:287` — `assertEqual(self.commit_count(), before)`; `scripts/test_unit_update_loop.py:219` — `self.assertEqual(_read(root)["no_diff_tasks"], ["T4"])` | ✅ PASS |

### LOOP-03: Self-healing repair loop

Entirely agent-facing prose. The approved Test Coverage Matrix (`tasks.md:26`) assigns prose "none — build gate only", so this is by design, but under evidence-or-zero none of these five criteria carries an executable assertion.

| Criterion | Spec-defined outcome | `file:line` | Result |
| --- | --- | --- | --- |
| AC 1 — failure keeps the phase open, no final state written | phase stays open | `references/recovery-loop.md:14`, `:87` | 📄 Prose-only |
| AC 2 — diagnose root cause; no unchanged retry | blind rerun is not a repair | `references/recovery-loop.md:27`, `:34` | 📄 Prose-only |
| AC 3 — never weaken/delete/skip a test to pass a gate | explicit prohibition | `references/recovery-loop.md:54-55` | 📄 Prose-only |
| AC 4 — repair and continue rather than report a blocker | repairable ≠ blocker | `references/recovery-loop.md:87-97` (classification table) | 📄 Prose-only |
| AC 5 — three-criteria external blocker → record, halt, no signature | evidence + halt, no done-signature | `references/recovery-loop.md:131-171`; `SKILL.md:294` | 📄 Prose-only |

### LOOP-04: Independent verification with bounded fix loop

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — fresh verifier dispatched, no prompting | author ≠ verifier | `SKILL.md:225-227`; `references/executors.md:133-134`; `references/checklist.md` verify section | 📄 Prose-only |
| AC 2 — verifier read-only over the real tree | no code/test modification | `SKILL.md:228-229` | 📄 Prose-only |
| AC 3 — FAIL routes gaps to `fix`, then re-dispatches verify | `phase=F` on FAIL+gaps, back to `phase=V` when gaps close | `scripts/test_unit_detect_phase.py:292` — `self.assertEqual(self.line(), "phase=F action=fix round=1")`; `:285` — `self.assertEqual(self.line(), "phase=V action=verify round=2")` (gaps 0 → verify); `:368` — FAIL report still yields `phase=F` | ✅ PASS |
| AC 4 — verify-round limit reached without PASS → halt and escalate | `phase=H reason=verify_exhausted`, checked before V or F | `scripts/test_unit_detect_phase.py:316` — `self.assertTrue(line.startswith("phase=H action=halt reason=verify_exhausted "), line)`; `:333-334` — `assertNotIn("phase=F", line)` + `assertIn("reason=verify_exhausted", line)`; `:338` — `assertEqual(self.line(), "phase=V action=verify round=100")` (omitted = unlimited); `:354` — pending work still dispatches at the ceiling | ✅ PASS |
| AC 5 — PASS confirmed with `validate_state.py`; non-zero = not done | `phase=E` only on exit 0 | `scripts/test_unit_detect_phase.py:362` — `self.assertEqual(self.line(), "phase=E action=done")`; `:368` — FAIL report → `phase=F`, not done; `scripts/test_int_end_to_end.py:398` — same against the **real** sibling validator | ✅ PASS |

### LOOP-05: Per-stage provider, model, and effort

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — resolve provider/model/effort and translate through the adapter table | per-provider command line | `scripts/test_unit_resolve_stage.py:76-77` — `assertIn("codex exec -m gpt-5.6-luna", line)` + `assertIn("-c model_reasoning_effort=max", line)`; `:93` — `assertIn("claude-opus-5[effort=high]", line)`; `:121-122` — `assertIn("--model opus", line)` + `assertIn("--effort high", line)` | ✅ PASS |
| AC 2 — unsupported effort rejected before dispatch | rejection names stage, provider, accepted values | `scripts/test_unit_config.py:165-166` — `assertIn("stages.verify", message)` + `assertIn("ultra", message)` (reachable path); `scripts/test_unit_resolve_stage.py:180-181` — `check_effort("claude","minimal","implement")` raises naming both; `:195-196` — `ultra` rejected for all three providers | ⚠️ Spec-precision gap (see below) |
| AC 3 — provider == running harness → native sub-agent | `kind=agent`, no CLI | `scripts/test_unit_resolve_stage.py:142` — `self.assertEqual(line, "kind=agent provider=claude model=opus effort=high")`; `:147` — `assertNotIn("cmd=", line)` | ✅ PASS |
| AC 4 — config read-only; runtime values recorded in `loop.json` | no write to `loop.config.toml` | `scripts/_config.py` exposes no writer (`load_config` only); `scripts/test_unit_init_loop.py:216` — `assertEqual(self.state()["harness_resolved"], "cursor")` (runtime value in state); `scripts/test_int_end_to_end.py:324` — state bytes unchanged across detects | ✅ PASS |
| AC 5 — launch/auth/quota failure halts with the reason recorded | `phase=H reason=executor`, resumable | `scripts/test_unit_update_loop.py:276-277` — `assertEqual(halt["reason"], "executor")` + `assertEqual(halt["detail"], "codex quota exhausted")`; `scripts/test_unit_detect_phase.py:382` — `assertIn("reason=executor", self.line())`. Trigger conditions are prose: `references/executors.md:203-206`, `references/recovery-loop.md:93` | ✅ PASS (recording/printing asserted; trigger is prose) |
| AC 6 — verify an executor's evidence before advancing | claim without artifact is not completion | `references/executors.md:61-71`, `:174-180` | 📄 Prose-only |

**⚠️ AC 2 spec-precision gap — T16's declaration independently confirmed.** `_config.EFFORTS = ("low","medium","high","xhigh","max")` (`scripts/_config.py:21`) rejects everything else at load time. `resolve_stage.PROVIDER_EFFORTS` (`:53-57`) gives `claude` and `cursor` exactly that set and `codex` a superset. `check_effort` (`:104`) also returns early for any provider absent from the table, so a custom `[providers.X]` cannot trigger it either. **No config-legal effort can reach the per-provider rejection.** The declaration in `tasks.md:549-554` is accurate; the branch is asserted directly on `check_effort` rather than end to end, which is the only option available. The reachable rejections — unknown provider and the cursor tier-suffix conflict — are covered through the CLI at `scripts/test_unit_resolve_stage.py:116` and `:225-227`.

### LOOP-06: Unattended continuation and stop conditions

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — re-enter detection in the same turn | no return of control while non-terminal | `SKILL.md:311-314` (in-turn gate, prose). Cross-turn analogue asserted: `scripts/test_int_loop_sh.py:177-178` — `assertEqual(self.spawns(), 4)` + `assertEqual(self.detect_calls(), 5)` over `0→B→V→F→E` | 📄 Prose-only (in-turn); ✅ for the driver |
| AC 2 — print the literal done-signature when `validate_state.py` exits 0 | `__TLC_LOOP__ feature=<feature> verify=PASS` | `SKILL.md:279-282`; parity verified across `references/checklist.md:132`, `assets/iteration-summary.template.md:36`, `assets/goal-condition.template.md:11`. `detect_phase` prints `phase=E action=done` (`test_unit_detect_phase.py:362`), the agent prints the signature. No assertion on the signature string. | 📄 Prose-only |
| AC 3 — resolve continuation from the harness, record it | `harness_resolved` in `loop.json` | `scripts/test_unit_init_loop.py:211` — `assertEqual(self.state()["harness_resolved"], "claude")`; `:216` — `"cursor"` | ✅ PASS |
| AC 4 — inconclusive detection halts and asks | non-zero exit, no state written, tells the user how | `scripts/test_unit_init_loop.py:223` — `assertNotEqual(proc.returncode, 0)`; `:228` — `assertIn("--respawn", proc.stderr)`; `:232` — `assertFalse(os.path.exists(self.state_path()))`; `:236-237` — two markers at once are also inconclusive | ✅ PASS |
| AC 5 — objective immutable for the run | verbatim at bootstrap, unwritable after | `scripts/test_unit_init_loop.py:199` — `assertEqual(self.state()["objective"], odd)` (whitespace and punctuation preserved); `scripts/test_unit_update_loop.py:142` — `assertEqual(_read(root)["objective"], OBJECTIVE)` after a rejected write; `:148` — `assertEqual(_read(root)["iteration"], 0)` (rejected call applies none of its other flags) | ✅ PASS |
| AC 6 — no new commit across N iterations → halt | `reason=no_progress` | `scripts/test_unit_detect_phase.py:387` — `assertIn("reason=no_progress", self.line())`; `scripts/test_unit_update_loop.py:182-184` — counter increments; `:193` — `assertEqual(..., 0)` on a recorded commit; `scripts/test_int_end_to_end.py:373` — `assertTrue(line.startswith("phase=H action=halt reason=no_progress "), line)` | ✅ PASS |
| AC 7 — same task's gate fails more than N attempts → halt | `reason=gate_stuck`, task named | `scripts/test_unit_detect_phase.py:393-394` — `assertIn("reason=gate_stuck", line)` + `assertIn("T4", line)`; `scripts/test_unit_update_loop.py:172` — `assertEqual(..., {"T3": 2, "T4": 1})` | ✅ PASS |
| AC 8 — `max_iterations` / `max_minutes` reached → write state and halt cleanly | `reason=limit` | `scripts/test_unit_detect_phase.py:399` — `assertIn("reason=limit", self.line())`; `:412` — `assertTrue(self.line().startswith("phase=B "), ...)` (omitted limit never fires) | ✅ PASS |
| AC 9 — remote/destructive operation → halt and wait for authorization | `reason=blast_radius`, no proceeding | `scripts/test_unit_detect_phase.py:375` — `assertTrue(line.startswith("phase=H action=halt reason=blast_radius "), line)` + `:376` — `assertIn('detail="push required"', line)`. The halt-and-wait discipline itself is prose: `SKILL.md:70-77`, `references/recovery-loop.md:97-112` | ✅ PASS (halt asserted); 📄 for the wait discipline |

**Count**: 37 P1 criteria. **24 ✅ PASS** with a spec-matched assertion · **12 📄 prose-only** (located in shipped prose, no executable assertion) · **1 ❌ GAP** (LOOP-01 AC 5b) · **1 ⚠️ spec-precision gap** (LOOP-05 AC 2, correctly declared by T16).

### P2: LOOP-07 — Handoff from tlc-spec-driven

**Not delivered.** T26 edits `~/.agents/skills/tlc-spec-driven/references/implement.md`, outside this repository, and awaits the user's go-ahead. Recorded as not-delivered, not as a failure. No verdict rendered.

---

## Edge Cases

| Edge case (spec.md:218-226) | Evidence | Handled? |
| --- | --- | --- |
| Not a git repository → halt at bootstrap | `scripts/test_unit_init_loop.py:142-143` — `assertNotEqual(proc.returncode, 0)` + `assertIn("git", proc.stderr.lower())` | ✅ |
| `tasks.md` missing or fails `validate_tasks.py` → refuse, report errors | `scripts/test_unit_init_loop.py:148-149`, `:154-155` — `assertIn("validate_tasks", proc.stderr)`; `:166` — no state written | ✅ |
| Duplicated `Task:` trailer → completed once **and record the ambiguity** | Counted once: `scripts/test_unit_gitio.py:122-124` — `assertEqual(ids.count("T1"), 1)` + `assertEqual(duplicates, ["T1"])`. **Recording: no evidence** — `scripts/detect_phase.py:147` binds the list to `_duplicates` and discards it; it is the only consumer. | ⚠️ Half handled |
| Uncommitted changes mapping to no task → halt and ask | `references/recovery-loop.md:96`, `:149` (prose; no worktree check in `detect_phase.py`) | 📄 Prose-only |
| Executor commits despite the ban → keep phase open, preserve work | `references/executors.md:20-30` (prose) | 📄 Prose-only |
| Batch worker reports a task failure → do not start the next batch | `SKILL.md` phase-B branch; `references/recovery-loop.md` (prose) | 📄 Prose-only |
| `.specs/loop.config.toml` absent → run on documented defaults | `scripts/test_unit_config.py:33-47` — full defaulted config asserted field by field; `:69-72` — every limit `None`; `scripts/test_unit_init_loop.py:187` — bootstrap succeeds with no config | ✅ |
| Configured provider CLI not installed → halt with the missing command named | `references/executors.md:205-206`, `references/recovery-loop.md:93` (prose). No `shutil.which` check in `resolve_stage.py`; `loop.sh:157-158` surfaces the non-zero exit but does not name it as a missing command. | 📄 Prose-only |

---

## Discrimination Sensor

**Isolation**: temporary `git worktree` at a scratchpad path, created from `HEAD` (`0468761`). Every mutation was applied to the worktree copy, tested there, then reverted with `git checkout --`. The worktree was removed with `git worktree remove --force` and pruned. `git status --porcelain` on the real tree was byte-identical to the pre-sensor baseline (both empty). No `git stash` was used at any point.

**Depth**: expanded (18 mutations), weighted to `checkpoint.py`, `detect_phase.py`, and `_gitio.completed_tasks` as instructed.

| # | File:line | Mutation | Killed? |
| --- | --- | --- | --- |
| M1 | `scripts/_gitio.py:60-62` | Dropped the empty-trailer skip — trailer-less commits become empty task ids | ✅ Killed |
| M2 | `scripts/_gitio.py:63-67` | Dropped dedupe — a duplicated `Task:` yields two ids and no duplicate report | ✅ Killed |
| M3 | `scripts/_gitio.py:50` | Removed `--reverse` — first-seen order becomes newest-first | ✅ Killed |
| M4 | `scripts/checkpoint.py:112` | Flipped the gate assertion — commits even when the gate did not pass | ✅ Killed |
| M5 | `scripts/checkpoint.py:153` | Ignored `check_commit.py`'s verdict — an invalid message still commits | ✅ Killed |
| M6 | `scripts/checkpoint.py:173` | Inverted the no-diff guard — a real diff is skipped, an empty one commits | ✅ Killed |
| M7 | `scripts/checkpoint.py:130-133` | Always append the trailer — a conforming message gets a duplicated `Task:` | ✅ Killed |
| M8 | `scripts/detect_phase.py:127-128` | Reverted T28 — unreadable state exits raw 1 instead of `phase=H reason=state_corrupt` | ✅ Killed |
| M9 | `scripts/detect_phase.py:195` | Off-by-one on the verify ceiling (`>=` → `>`) — the limit fires one round late | ✅ Killed |
| M10 | `scripts/detect_phase.py:151` | Ignored git trailers — completion no longer derives from git | ✅ Killed |
| M11 | `scripts/detect_phase.py:80` | Off-by-one on `no_progress_iterations` | ✅ Killed |
| M12 | `scripts/detect_phase.py:139-140` | Dropped the halt-first check — a recorded halt no longer outranks work | ✅ Killed |
| M13 | `scripts/_config.py:56` | Restored the hard-coded `max_rounds` default of 3 (T29 regression) | ✅ Killed |
| M14 | `.gitignore:7` | Dropped the `loop.json` ignore rule (T30 regression) | ✅ Killed |
| M15 | `scripts/_batching.py:63` | Off-by-one on the tail-folding threshold (`<= 2` → `<= 1`) | ✅ Killed |
| M16 | `scripts/update_loop.py:166` | Dropped the iteration-log cap side effect | ✅ Killed |
| M17 | `scripts/resolve_stage.py:135` | Never take the native-agent path (LOOP-05 AC 3) | ✅ Killed |
| M18 | `scripts/init_loop.py:73` | Guess the first harness when markers for two are set (LOOP-06 AC 4) | ✅ Killed |

**Result**: 18/18 killed, 0 survived — ✅

**Isolation check**: `git worktree list` shows only the real tree; `git status --porcelain` empty; `git rev-parse HEAD` = `0468761` — identical to the pre-sensor baseline.

---

## Independent Check of the Authors' Self-Declared Claims

**1. Batch 4 rewrote four pre-existing tests — "the spec changed, not weakening". CONFIRMED.**
`spec.md` was itself amended inside the diff range (commit `1190e47`): LOOP-01's old AC 3 ("absent *or unparseable* → reconstruct") was split into AC 3 (absent → reconstruct) and AC 4 (unparseable → `phase=H reason=state_corrupt`). The two rewritten tests in `test_unit_detect_phase.py` track that split exactly, and the swap was **net additive**: two tests asserting `returncode == 1` + stderr became five tests asserting the halt line, the reason, the detail, exit 0 with empty stderr, and that corrupt state is never reconstructed into work (`:451-480`), plus a new `AbsentState` class (`:210-231`). No assertion lost precision.
The two `test_unit_config.py` changes swapped `assertEqual(cfg["verify"]["max_rounds"], 3)` for `assertIsNone(...)` at `:34` and `:121` and added two new tests (`:85-94`). Same precision, opposite value. The new value is what `spec.md`'s own assumption row D5 demands ("Ceiling on verify rounds: **Configurable, no hard-coded maximum**") and what LOOP-04 AC 4's word "**configured**" means. M13 proves the swap is load-bearing: reinstating the `3` default kills the suite.

**2. T29 exceeded its declared `Where`. CONFIRMED, and justified — but with one stale document.**
T29 declared `Where: scripts/detect_phase.py` and touched 12 files. The `_config.py:56` change is genuinely required: with a hard default of `3`, T29's own Done-when "an omitted `max_rounds` means unlimited" was unreachable, and assumption D5 forbids a hard-coded maximum. The five re-documented files are consistent with the code — `config-schema.md:113` ("unlimited"), `:115`, `state-schema.md:141-144`, `checklist.md:99-102`, `loop.config.example.toml:57-58`, `SKILL.md:240-244` all describe the detector-owned ceiling and the omitted-is-unlimited rule. **No document describes behaviour the code lacks.**
The inverse failed, and is Gap 3 below: `SKILL.md:290-291` still enumerates "Implemented reasons: `no_progress`, `gate_stuck`, `executor`, `limit`, `blocker`, `blast_radius`" — omitting `state_corrupt` and `verify_exhausted`, which `detect_phase.py:127` and `:197` print and `update_loop.py:43-52` accepts. T21's note explicitly deferred `state_corrupt` "until T28 lands it"; T28 landed it and updated `phase-transitions.md:63` but not `SKILL.md`.

**3. T16's spec-precision gap. CONFIRMED, correctly declared.** See the LOOP-05 AC 2 note above — genuinely unreachable through any legal configuration, including a custom `[providers.X]` table.

**4. `ff51fc9` carries no `Task:` trailer by design. CONFIRMED, and harmless.**
Three commits in the range carry no `Task:` trailer: `1190e47`, `ff51fc9`, `edbe5a0`. `_gitio.completed_tasks` skips empty trailer lines at `scripts/_gitio.py:60-62`, so they contribute nothing. Run against the real repository the function returns 29 ids, no duplicates, no empty entries. The commit's own reasoning is sound: reusing `T18`/`T20` would have created the duplicate-trailer ambiguity. M1 proves the skip is load-bearing.

**5. T25 reports a vacuous forward-dependency check in `validate_tasks.py`. CONFIRMED, and the characterization tests are discriminating.**
`parse_phase_membership` (sibling `validate_tasks.py:111-128`) maps a task only when its own `### TN:` header follows a `### Phase N` header, and never leaves phase mode — so under the standard template layout every task is attributed to the last phase heading, and `p_dep > p_here` (`:196`) can never be true.
**Discrimination proven empirically**, not argued: a patched sibling that also honours ids named inside a phase's diagram fence was placed in the scratch, and `test_the_standard_template_layout_hides_a_forward_phase_dependency` **failed** with its intended message ("the forward-dependency defect appears to be fixed; delete this characterization test"). Separately, patching `if t["tests"] is None:` → `if not t["tests"]:` made `test_an_empty_tests_field_counts_as_present` **fail**. Both characterization tests are real sensors, not silent pass-throughs. The scratch sibling was deleted; the installed sibling at `~/.agents/skills/tlc-spec-driven/` was never modified.

---

## Payload / Conjunction Rule

Checked for every named field in a returned object or written file. No instance of "the call ran" standing in for "the value is right":

- `checkpoint.py` — the trailer **values** are read back out of git (`test_unit_checkpoint.py:206`, `:211`), not merely counted; the message handed to `check_commit.py` is compared byte for byte (`:184`); the committed **file list** is asserted (`:340`, `:345`).
- `_state_io.new_state` — every field of the initial shape asserted individually (`test_unit_state_io.py:32-48`), including the absence of `completed_tasks` (`:53`).
- `update_loop.py` — each counter asserted on value, not on exit code: `{"T3": 2, "T4": 1}` (`:172`), `iterations_without_commit` 1→2→0 (`:182-193`), log contents and ordering after the cap (`:109-112`).
- `_config.load_config` — the whole default tree asserted key by key (`test_unit_config.py:33-65`).
- `resolve_stage` — the rendered command **line** asserted, and `kind=agent` compared as a complete string (`:142`).
- `_gitio.completed_tasks` — both tuple elements asserted, including that `duplicates` is empty on the happy path (`test_unit_checkpoint.py:257`).
- `test_int_end_to_end.assert_no_executor_ran` (`:272-276`) is a negative assertion whose discrimination the authors verified by driving the same fixture at `phase=B`, where the marker does appear.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ stdlib only; no dependency added |
| Surgical changes | ⚠️ T29 touched 12 files against a one-file `Where`; the expansion is justified by D5 and declared in `tasks.md:1004-1022`, but the declared `Where` was not updated |
| No scope creep | ✅ nothing beyond the spec; out-of-scope items in `spec.md:28-37` are respected |
| Matches patterns | ✅ every module carries the same docstring-first, AC-referencing style |
| Spec-anchored outcome check | ✅ for the 24 code-realizable ACs; gaps flagged rather than passed silently |
| Per-layer Coverage Expectation met | ✅ support modules and CLI entrypoints have per-branch tests; prose has build-gate only, per the approved matrix (`tasks.md:26`) |
| Every test maps to a spec requirement | ✅ every module docstring names its ACs; no unclaimed tests found |
| Documented guidelines followed | ✅ none exist — strong defaults applied (stdlib `unittest`, tmpdir-scoped, zero dependencies), as recorded in `tasks.md:18` |
| Hook bypass | ✅ `--no-verify` absent from `checkpoint.py`, asserted at `test_unit_checkpoint.py:394` |

---

## Gate Check

- **Gate command** (Build, from `tasks.md:36`): `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Result**: **289 passed, 0 failed, 0 skipped** (29.2s, exit 0)
- **Test count before feature**: 0 — `12bd8c3` is the planning-docs commit of a greenfield repository
- **Test count after feature**: 289
- **Delta**: +289
- **Skipped tests**: none. `test_int_tlc_validators` and `test_int_end_to_end` skip only when the sibling skill is absent; it is installed at `~/.agents/skills/tlc-spec-driven/`, so both ran against the real validators.
- **Failures**: none
- `compileall` and `bash -n scripts/loop.sh` both clean.

---

## Fix Plans

### Fix 1: LOOP-01 AC 5b — nothing records the reconciliation

- **Priority**: Major (an explicit `SHALL` with no implementation and no evidence)
- **Root cause**: `detect_phase.py` is read-only by design, so it cannot record; no other component was given the job, and `_state_io.REQUIRED_KEYS` has no field for it.
- **Fix task** — *What*: record a git-versus-state reconciliation when detection finds `current_task` or `current_batch` naming a task git already reports complete. *Where*: `scripts/update_loop.py` (a new flag), `scripts/_state_io.py` (the field), `references/state-schema.md`. Keep `detect_phase.py` read-only — the agent records it in the same iteration it observes it, exactly as `--no-diff` works today. *Verify*: a unit test asserting the recorded field's value after a reconciliation, plus a detect test proving detection still writes nothing. *Done when*: the field is documented in `state-schema.md`, written only by `update_loop.py`, and asserted on value.

### Fix 2: Edge case — duplicate `Task:` trailer ambiguity is dropped, and a shipped doc says otherwise

- **Priority**: Minor
- **Root cause**: `scripts/detect_phase.py:147` discards `_duplicates`, the sole consumer of the value `_gitio` computes. `references/phase-transitions.md:108` states "The duplication is reported rather than dropped", which the shipped pipeline does not do.
- **Fix task** — *What*: surface the duplication (a `dup=` field on the phase line, or record it through `update_loop.py` alongside Fix 1). *Where*: `scripts/detect_phase.py`, `references/phase-transitions.md`. *Verify*: a detect test building a cherry-picked duplicate and asserting the emitted or recorded value. *Done when*: the doc sentence is true of the code, or the doc is corrected to say the value stops at `_gitio`.

### Fix 3: `SKILL.md` halt-reason enumeration is stale

- **Priority**: Minor
- **Root cause**: T28 and T29 added `state_corrupt` and `verify_exhausted` to `detect_phase.py` and to `phase-transitions.md:63`, but not to the Phase H enumeration in `SKILL.md:290-291`. T21's mechanical enum-parity check ran before either landed and was never re-run.
- **Fix task** — *What*: add both reasons to `SKILL.md:290-291`. *Where*: `SKILL.md`. *Verify*: re-run T21's enum-parity check — every reason named in the shipped prose must appear in `update_loop.HALT_REASONS`, and vice versa. *Done when*: `SKILL.md`, `references/phase-transitions.md:63`, and `update_loop.py:43-52` agree. Consider pinning the parity as a test so it cannot go stale again.

### Observation (not a fix task): prose-only criteria

Twelve P1 criteria — all of LOOP-03, LOOP-04 AC 1–2, LOOP-02 AC 5, LOOP-05 AC 6, LOOP-06 AC 1–2 — are realized as agent-facing instructions with no executable assertion. This is what the approved Test Coverage Matrix specifies for prose, and it is intrinsic to a skill whose deliverable is partly instructions. It is recorded here so the residual risk is visible, not as a defect: these behaviours are guaranteed by the model following `SKILL.md` and `references/`, and the build gate proves only that the documents exist and are internally linked. Fix 3 is a live example of how that residual risk materializes.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| LOOP-01 | Pending | ❌ Needs Fix (AC 5b unrecorded; AC 1–4, 5a, 6 verified) |
| LOOP-02 | Pending | ✅ Verified (AC 5 prose-only) |
| LOOP-03 | Pending | ⚠️ Documented only — no executable evidence |
| LOOP-04 | Pending | ✅ Verified (AC 1–2 prose-only) |
| LOOP-05 | Pending | ✅ Verified (AC 2 spec-precision gap declared; AC 6 prose-only) |
| LOOP-06 | Pending | ✅ Verified (AC 1–2 prose-only) |
| LOOP-07 | Pending | ⛔ Not delivered (P2, out of scope) |

---

## Summary

**Overall**: ⚠️ Issues — three grounded gaps, none blocking a re-run of the loop, all cheap to close.

**Spec-anchored check**: 24/37 P1 ACs matched the spec-defined outcome with a `file:line` assertion · 12 prose-only · 1 gap · 1 spec-precision gap (correctly declared)
**Sensor**: 18/18 mutations killed, 0 survived
**Gate**: 289 passed, 0 failed, 0 skipped

**What works**: Phase detection is genuinely derived, not stored — deleting `loop.json` mid-run reproduces the same next task, proven end to end against the real sibling validators. Checkpointing refuses on every path it should and never double-writes a trailer. The halt vocabulary is complete in the code and ordered so a halt outranks work. Every counter a halt condition reads is written by exactly one script, and the sensor confirms each of those counters is load-bearing. The four self-declared claims all hold, including T25's characterization tests, which were empirically shown to fail against a fixed sibling.

**Issues found**:
1. LOOP-01 AC 5b — "record the reconciliation in `loop.json`" is unimplemented and unevidenced.
2. Spec edge case — a duplicated `Task:` trailer is counted once but the ambiguity is dropped, while `references/phase-transitions.md:108` says it is reported.
3. `SKILL.md:290-291` under-describes the halt vocabulary: `state_corrupt` and `verify_exhausted` are missing.

**Next steps**: Route Fixes 1–3 to an implementer, then re-dispatch the Verifier (iteration 1 of a maximum of 3). LOOP-07 / T26 stays parked until the user authorizes editing the sibling skill.
