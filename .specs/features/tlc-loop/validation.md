# tlc-loop Validation

**Date**: 2026-08-08
**Round**: **3 of a maximum 3** (round 1 FAIL → T31-T33; round 2 PASS at `bdacb95`; round 3 re-verifies the whole after `bdacb95..HEAD`)
**Spec**: `.specs/features/tlc-loop/spec.md`
**Diff range**: `12bd8c3..HEAD` (HEAD = `13c155a`, 38 commits). Delta since the last verification: `bdacb95..HEAD` = `6ea5ad5`, `0689638` (T26), `bb9daec`, `eeb2296`, `c7d4cfe` (T34), `13c155a` (T35).
**Verifier**: independent sub-agent, round 3 — did not write the code, did not write the round-1 or round-2 report. Coverage re-derived from `spec.md` from scratch; both prior reports were treated as claims to re-test.
**Scope**: all 39 acceptance criteria. **LOOP-07 is in scope this round** — T26 shipped at `0689638`, so the round-2 "not delivered" record no longer applies.

---

## Verdict

**Result: FAIL** — 4 ranked gaps, all documentation-accuracy or test-coverage, none an unimplemented `SHALL`.

The engineering is sound. The gate is green at **325 passed / 0 failed / 0 skipped**, the sensor killed **11/11** injected faults, **25/39** acceptance criteria carry a `file:line` assertion whose asserted value matches the spec-defined outcome, and **0** criteria are unevidenced. T34 genuinely closes the hole it was written for: I attacked it with an amended commit, a reverted/restored SHA, a detached HEAD, an empty repository, and the verify-ceiling interaction, and it held on all five. `detect_phase.py` is proven side-effect free — not assumed — including on the new `git rev-parse` path.

What fails is the prose. This skill's shipped product **is** its prose, and T34 changed a contract that four sentences across `README.md` and `references/state-schema.md` still describe the old way. Two of those sentences are provably false of the code, and one of them is contradicted by another sentence in the same file. That is the identical failure mode as round-1 Gap 3 (`references/phase-transitions.md` claiming behaviour the code did not have), which was ranked a FAIL gap and fixed by T32/T33. The same standard applied consistently yields FAIL here.

Separately, the sensor found a mutation that **survives the gate T34 itself declares**: removing the `verified_at` stamp from `update_loop.py` passes all 272 unit tests. T34 declares `Gate: quick`.

All four gaps are cheap: three prose edits and one unit test. Ranked in §7.

---

## 1. Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1–T13 | ✅ Done | Foundation, detection, state mutation, checkpoint, bootstrap |
| T14 | ⚠️ Partial | codex environment marker UNRESOLVED — recorded rather than guessed; `init_loop.HARNESS_MARKERS` (`scripts/init_loop.py:54-57`) carries `claude` and `cursor` only. Deviation declared in `tasks.md`. Unchanged from rounds 1–2 |
| T15–T25 | ✅ Done | Providers, executors, recovery, driver, skill assembly, validator mutation tests |
| T26 | ✅ Done | `0689638` — **newly delivered this round**. Implementation lands outside this repository; see §5 |
| T27–T33 | ✅ Done | End-to-end, corrupt-state halt, verify ceiling, loop-state ignore, round-1 fixes |
| T34 | ✅ Done | `c7d4cfe` — stale-verification refusal. Verified in depth in §3 |
| T35 | ✅ Done (with defects) | `13c155a` — README. Four of its factual claims checked; two are wrong. See §4 |

Verified live against this repository: `_gitio.completed_tasks('.')` returns **35 unique ids** (T1–T35), **0 duplicates**, **0 empty entries**; `_tasksmd.parse` finds 35 planned, 35 ticked, 0 pending. `reconciled` computes to `[]` — plan and git agree exactly.

**Process note (not a gap).** Three of the six delta commits carry no `Task:` trailer: `6ea5ad5` (SKILL.md audit fixes), `bb9daec` (plan update adding T34/T35), `eeb2296` (the characterization-test inversion). `SKILL.md:58-60` says "never commit outside `checkpoint.py`". No AC forbids untrailered commits and `eeb2296`'s test is claimed by T25's requirement, so this is a dogfooding-discipline observation, not a defect.

---

## 2. Spec-Anchored Acceptance Criteria (re-derived, evidence-or-zero)

Legend: ✅ PASS (assertion targets the spec-defined outcome) · 📄 Prose-only (realized as agent-facing instruction; located, no executable assertion) · ⚠️ Spec-precision gap · ❌ GAP.

Line numbers were re-resolved against the current tree; `test_unit_detect_phase.py` shifted by up to +49 lines when `StaleVerification` was inserted, so round-2 citations no longer hold verbatim.

### LOOP-01: Deterministic phase detection and resume

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — exactly one phase line before any work | one line, documented vocabulary | `scripts/test_unit_detect_phase.py:197` — `assertEqual(len(lines), 1, f"expected exactly one line, got {lines!r}")`, the gate on **every** `line()` call in the file; `:203` — `assertEqual(self.line(), "phase=0 action=bootstrap")`; `:351` — one line even with three reconciliations | ✅ PASS |
| AC 2 — git trailers authoritative over `loop.json` | git wins over conflicting state | `scripts/test_unit_detect_phase.py:267` — `assertEqual(self.line(), "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6")` while state still claims `current_task="T1"` and `current_batch=["T1","T2","T3"]`; `scripts/test_unit_gitio.py:91` — `assertEqual(ids, ["T2", "T1"])` (first-committed order) | ✅ PASS |
| AC 3 — absent `loop.json` reconstructs | same next task git implies, no failure | `scripts/test_unit_detect_phase.py:225` → `:228` → `:231` — `assertEqual(self.line(), before)` after delete + re-bootstrap; `scripts/test_int_end_to_end.py:344/346/348` — same over the real sibling layout | ✅ PASS |
| AC 4 — unparseable `loop.json` halts `state_corrupt` | `phase=H reason=state_corrupt`, no reconstruction | `scripts/test_unit_detect_phase.py:671` — `assertTrue(self.line().startswith("phase=H action=halt reason=state_corrupt "))`; `:677` — `assertIn("malformed JSON", line)`; `:697` — `assertNotIn("phase=B", self.line())`; `:683-684` — exit 0, empty stderr | ✅ PASS |
| AC 5 — git is truth **and** the reconciliation is recorded | git decides; durable record of the override | Git wins: `:267`, `:309` (`assertIn("tasks=T1,", self.line())`). Surfaced: `:297` — whole-line `"…tasks=T1,T2,T3,T4,T5,T6 reconciled=T1"`. Recorded on value: `scripts/test_unit_update_loop.py:254-256` — `task`/`winner`/`at` each asserted. Durable: `scripts/test_unit_state_io.py:75-77`. Idempotent: `scripts/test_unit_update_loop.py:274-276` | ✅ PASS |
| AC 6 — `loop.json` mutated only through its own script | single writer; detect writes nothing | `scripts/test_unit_detect_phase.py:633-646` — state bytes + porcelain + HEAD unchanged; `:336-343` (with `reconciled=` active), `:409-416` (with `dup=` active); `scripts/test_unit_update_loop.py:130` — `assertNotEqual(proc.returncode, 0)` on an objective write. **Independently re-proven for the new `git rev-parse` call** — see §3.2 | ✅ PASS |

### LOOP-02: Atomic checkpoint per task

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — one atomic commit with `Task:` and `Gate: <level> PASS` | trailers readable back via `%(trailers:key=Task,valueonly)` | `scripts/test_unit_checkpoint.py:201` — `assertEqual(self.commit_count(), before + 1)`; `:206` — `assertEqual(self.trailer("Task"), "T7")`; `:211` — `assertEqual(self.trailer("Gate"), "build PASS")` | ✅ PASS |
| AC 2 — no passing gate, no commit | refusal; commit count unchanged | `:141-142` (gate omitted), `:148-149` (`FAIL`), `:155-156` (lowercase `pass`) — each `assertNotEqual(proc.returncode, 0)` + `assertEqual(self.commit_count(), before)`; `:161` — the work is preserved, not discarded | ✅ PASS |
| AC 3 — validate with `check_commit.py`, abort on non-zero | validated **before** staging | `:171-172` — refusal + no commit; `:177` — `assertEqual(self.staged(), [])`; `:184` — `assertEqual(fh.read(), GOOD_MESSAGE)` (the payload handed over is asserted, not just that the call happened) | ✅ PASS |
| AC 4 — at most one commit per task, never batched | one commit; repeated `Task:` refused or deduped | `:201`; `:242`/`:247` — a message already carrying the trailers yields exactly one of each; `:256-257` — `assertEqual(ids, ["T7"])` + `assertEqual(duplicates, [])`; `:263-264`, `:270-271` — a contradicting trailer refused | ✅ PASS |
| AC 5 — executor forbidden from committing; the loop checkpoints | prohibition + ownership | `references/executors.md:20`; `SKILL.md:62`; `references/checklist.md:74-76`. Orchestrator-side checkpointing exercised at `scripts/test_int_end_to_end.py:326-332`, but the prohibition carries no executable assertion | 📄 Prose-only |
| AC 6 — no file changes → record completion, no fabricated diff | `SKIP: no changes`, exit 0, no commit | `scripts/test_unit_checkpoint.py:279` — `assertIn("SKIP: no changes", proc.stdout)`; `:282` — exit 0; `:287` — commit count unchanged; `scripts/test_unit_update_loop.py:219` — `assertEqual(_read(root)["no_diff_tasks"], ["T4"])` | ✅ PASS |

**Edge case (`spec.md:220`) — duplicated `Task:` trailer**: counted once `scripts/test_unit_gitio.py:122-124` (over a fixture whose own guard at `:119` asserts the duplication is real); surfaced `scripts/test_unit_detect_phase.py:372-375`, `:389`, `:402`, `:432-436`. ✅ both halves.

### LOOP-03: Self-healing repair loop

Entirely agent-facing prose. The approved Test Coverage Matrix (`tasks.md:26`) assigns prose "none — build gate only", so this is by design; under evidence-or-zero none of the five carries an executable assertion.

| Criterion | Spec-defined outcome | `file:line` | Result |
| --- | --- | --- | --- |
| AC 1 — failure keeps the phase open, no final state written | phase stays open | `references/recovery-loop.md:12`; `references/checklist.md:20-24` | 📄 Prose-only |
| AC 2 — diagnose root cause; no unchanged retry | a blind rerun is not a repair | `references/recovery-loop.md:27`, `:34` | 📄 Prose-only |
| AC 3 — never weaken/delete/skip a test to pass a gate | explicit prohibition | `references/recovery-loop.md:54`; `SKILL.md:66-68`; `references/checklist.md:113-115` | 📄 Prose-only |
| AC 4 — repair and continue rather than report a blocker | repairable ≠ blocker | `references/recovery-loop.md:82-96`, `:142-151` | 📄 Prose-only |
| AC 5 — three-criteria external blocker → record, halt, no signature | evidence + halt, no done-signature | `references/recovery-loop.md:126-167`; `SKILL.md:314-316` | 📄 Prose-only |

### LOOP-04: Independent verification with bounded fix loop

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — fresh verifier dispatched, no prompting | author ≠ verifier | `SKILL.md:233-234`; `references/executors.md:133-135`; `references/checklist.md:80-84` | 📄 Prose-only |
| AC 2 — verifier read-only over the real tree | no code/test modification | `SKILL.md:236`; `references/executors.md:136-138`; `references/checklist.md:85-87` | 📄 Prose-only |
| AC 3 — FAIL routes gaps to `fix`, then re-dispatches verify | `phase=F` on FAIL+open gaps; back to `phase=V` when gaps close | `scripts/test_unit_detect_phase.py:460` — `assertEqual(self.line(), "phase=F action=fix round=1")`; `:453` — `assertEqual(self.line(), "phase=V action=verify round=2")` with gaps 0; `:543` — a FAIL report still yields `phase=F` | ✅ PASS |
| AC 4 — verify-round limit reached without PASS → halt and escalate | `phase=H reason=verify_exhausted`, checked ahead of V and F | `:485` — `assertTrue(line.startswith("phase=H action=halt reason=verify_exhausted "))`; `:501-502` — `assertNotIn("phase=F", line)` + `assertIn("reason=verify_exhausted", line)`; `:506` — omitted `max_rounds` never halts (`round=100`); `:525` — pending work still dispatches at the ceiling | ✅ PASS |
| AC 5 — PASS confirmed with `validate_state.py`; non-zero = not done | `phase=E` only on exit 0 — **and, since T34, only while the verdict covers HEAD** | `:537` — `assertEqual(self.line(), "phase=E action=done")` with `verified_at == HEAD`; `:569` — a commit after the PASS → `assertEqual(self.line(), "phase=V action=verify round=2")`; `:576` — PASS covering HEAD → `phase=E`; `:583` — no recorded verification → `phase=V action=verify round=1`; `:516` — PASS at the ceiling covering HEAD → `phase=E`; `:543` — FAIL report → `phase=F`; `scripts/test_int_end_to_end.py:414` and `:426` — both against the **real** sibling validator | ✅ PASS *(strengthened this round)* |

### LOOP-05: Per-stage provider, model, and effort

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — resolve provider/model/effort, translate through the adapter table | per-provider command line | `scripts/test_unit_resolve_stage.py:76-77` — `assertIn("codex exec -m gpt-5.6-luna", line)` + `assertIn("-c model_reasoning_effort=max", line)`; `:93` — `assertIn("claude-opus-5[effort=high]", line)`; `:125-126` — `assertIn("--model opus", line)` + `assertIn("--effort high", line)` | ✅ PASS |
| AC 2 — unsupported effort rejected before dispatch | rejection names stage, provider, accepted values | `scripts/test_unit_config.py:165-166` — `assertIn("stages.verify", message)` + `assertIn("ultra", message)` (the reachable path); `scripts/test_unit_resolve_stage.py:180-181`, `:193-196` | ⚠️ Spec-precision gap (note below) |
| AC 3 — provider == running harness → native sub-agent | `kind=agent`, no CLI | `scripts/test_unit_resolve_stage.py:142` — `assertEqual(line, "kind=agent provider=claude model=opus effort=high")`; `:147` — `assertNotIn("cmd=", line)` | ✅ PASS |
| AC 4 — config read-only; runtime values recorded in `loop.json` | no write to `loop.config.toml` | `scripts/_config.py` exposes no writer (`load_config` only); `scripts/test_unit_init_loop.py:216` — `assertEqual(self.state()["harness_resolved"], "cursor")`; `scripts/test_int_end_to_end.py:324` — `assertEqual(self.state_bytes(), before)` | ✅ PASS |
| AC 5 — launch/auth/quota failure halts with the reason recorded | `phase=H reason=executor`, resumable | `scripts/test_unit_update_loop.py:330-331` — `assertEqual(halt["reason"], "executor")` + `assertEqual(halt["detail"], "codex quota exhausted")`; `scripts/test_unit_detect_phase.py:599` — `assertIn("reason=executor", self.line())`. Trigger conditions are prose (`references/executors.md:203-206`) | ✅ PASS (recording and printing asserted) |
| AC 6 — verify an executor's evidence before advancing | a claim without an artifact is not completion | `references/executors.md:61-71`, `:174-180`; `references/checklist.md:61-65` | 📄 Prose-only |

**⚠️ AC 2 note — independently re-confirmed for the third time.** `_config.EFFORTS` (`scripts/_config.py:21`) rejects anything outside `low/medium/high/xhigh/max` at load time; `resolve_stage.PROVIDER_EFFORTS` (`:53-57`) gives `claude` and `cursor` exactly that set and `codex` a superset, and `check_effort` returns early for any provider absent from the table. No config-legal effort can reach the per-provider rejection, so that branch is asserted directly on `check_effort` rather than end to end. `tasks.md` declares this accurately. Untouched by the delta.

### LOOP-06: Unattended continuation and stop conditions

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — re-enter detection in the same turn | control not returned while non-terminal | `SKILL.md:326-329` (in-turn gate, prose); `references/checklist.md:34-36`. Cross-turn analogue asserted: `scripts/test_int_loop_sh.py:177-178` — `assertEqual(self.spawns(), 4)` + `assertEqual(self.detect_calls(), 5)` over `0→B→V→F→E` | 📄 Prose-only (in-turn); ✅ for the driver |
| AC 2 — print the literal done-signature when `validate_state.py` exits 0 | `__TLC_LOOP__ feature=<feature> verify=PASS` | `SKILL.md:286-289`; parity across `references/checklist.md:131-132`, `assets/iteration-summary.template.md:36`, `assets/goal-condition.template.md:11`. `detect_phase` prints `phase=E action=done` (`test_unit_detect_phase.py:537`); the agent prints the signature. No assertion on the signature string | 📄 Prose-only |
| AC 3 — resolve continuation from the harness, record it | `harness_resolved` in `loop.json` | `scripts/test_unit_init_loop.py:212` — `assertEqual(self.state()["harness_resolved"], "claude")`; `:216` — `"cursor"`; `:242`, `:252` — explicit/configured `--respawn` records `"codex"` | ✅ PASS |
| AC 4 — inconclusive detection halts and asks | non-zero exit, no state written, tells the user how | `:224` — `assertNotEqual(proc.returncode, 0)`; `:228` — `assertIn("--respawn", proc.stderr)`; `:232` — `assertFalse(os.path.exists(self.state_path()))`; `:236-237` — two markers at once are also inconclusive | ✅ PASS |
| AC 5 — objective immutable for the run | verbatim at bootstrap, unwritable after | `scripts/test_unit_init_loop.py:200` — `assertEqual(self.state()["objective"], odd)`; `scripts/test_unit_update_loop.py:142` — unchanged after a rejected write; `:148` — `assertEqual(_read(root)["iteration"], 0)`, so a rejected call applies none of its other flags | ✅ PASS |
| AC 6 — no new commit across N iterations → halt | `reason=no_progress` | `scripts/test_unit_detect_phase.py:604` — `assertIn("reason=no_progress", self.line())`; `scripts/test_unit_update_loop.py:182-184` — counter 1→2; `:193` — reset to 0 on a recorded commit; `scripts/test_int_end_to_end.py:373` — `assertTrue(line.startswith("phase=H action=halt reason=no_progress "))` | ✅ PASS |
| AC 7 — same task's gate fails more than N attempts → halt | `reason=gate_stuck`, task named | `scripts/test_unit_detect_phase.py:610-611` — `assertIn("reason=gate_stuck", line)` + `assertIn("T4", line)`; `scripts/test_unit_update_loop.py:172` — `assertEqual(..., {"T3": 2, "T4": 1})` | ✅ PASS |
| AC 8 — `max_iterations` / `max_minutes` reached → write state, halt cleanly | `reason=limit` | `scripts/test_unit_detect_phase.py:616` — `assertIn("reason=limit", self.line())`; `:625` — `assertTrue(self.line().startswith("phase=B "))` when the limit is omitted | ✅ PASS |
| AC 9 — remote/destructive operation → halt and wait for authorization | `reason=blast_radius`, no proceeding | `scripts/test_unit_detect_phase.py:592-593` — `assertTrue(line.startswith("phase=H action=halt reason=blast_radius "))` + `assertIn('detail="push required"', line)`. The wait discipline is prose: `SKILL.md:70-77`; `references/checklist.md:143-145` | ✅ PASS (halt asserted); 📄 for the wait discipline |

### LOOP-07: Handoff from tlc-spec-driven — **in scope this round**

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — Execute with a >1-batch `tasks.md` presents loop mode alongside inline and sub-agents | three options, one line each, invocation named | `~/.agents/skills/tlc-spec-driven/references/sub-agents.md:40-46` — the offer block; `:44` names `` `/tlc-loop [feature]` `` with its one-line rationale. Trigger gated at `~/.agents/skills/tlc-spec-driven/references/implement.md:35` and `SKILL.md:46` ("> ~8 tasks"). No executable assertion | 📄 Prose-only |
| AC 2 — declining falls back to existing behaviour unchanged | inline path preserved | `~/.agents/skills/tlc-spec-driven/references/sub-agents.md:48` — "The user must explicitly accept. If they decline (or if the feature fits one batch), execute inline."; `:50` — degrades to the original two options when `tlc-loop` is absent, so the sibling stays optional. No executable assertion | 📄 Prose-only |

**Durability caveat (Gap 4).** LOOP-07's entire deliverable lives outside this repository, in a directory that is **not** under version control (`git rev-parse` in `~/.agents/skills/tlc-spec-driven` → "not a git repository"). It is absent from the diff surface, absent from the build gate, and has already drifted: comparing `~/.agents/skills/.tlc-spec-driven.backup-20260808` against the live sibling shows three unrelated post-T26 changes (the batching overflow guard in `sub-agents.md:22-33`, `validate_spec.py:160`, `validate_tasks.py:111-165`). The backup the T26 commit message cites as "taken before the edit" already contains the loop-mode offer, so it cannot substantiate the "byte-for-byte unchanged" Done-when either. A reinstall of `tlc-spec-driven` from upstream silently reverts LOOP-07 and nothing here notices.

### Count (re-derived independently — not copied from round 2)

**39 criteria**: LOOP-01 ×6, LOOP-02 ×6, LOOP-03 ×5, LOOP-04 ×5, LOOP-05 ×6, LOOP-06 ×9, LOOP-07 ×2.

| Result | Count | Where |
| --- | --- | --- |
| ✅ PASS with a spec-matched assertion | **25** | LOOP-01 ×6, LOOP-02 ×5, LOOP-04 ×3, LOOP-05 ×4, LOOP-06 ×7 |
| 📄 Prose-only (located, no executable assertion) | **13** | LOOP-02 AC 5; LOOP-03 ×5; LOOP-04 AC 1–2; LOOP-05 AC 6; LOOP-06 AC 1–2; LOOP-07 ×2 |
| ⚠️ Spec-precision gap (declared) | **1** | LOOP-05 AC 2 |
| ❌ GAP (no evidence) | **0** | — |

Round 2 reported 25/37 over P1 only. My P1 sub-count is identical (25 ✅ / 11 📄 / 1 ⚠️); the delta is purely LOOP-07's two prose criteria entering scope. **The prose-only total is therefore 13, not 11** — which makes `README.md:181` stale (Gap 3).

---

## 3. T34 under attack — does the staleness check actually close the hole?

### 3.1 Is there any path where a PASS is accepted while HEAD has moved?

Probed against a disconnected full copy of this repository in the session scratchpad, with `verify.verified_at` set by hand and `detect_phase.py` run for real.

| Attack | Setup | Line printed | Correct? |
| --- | --- | --- | --- |
| Baseline (this repo as it stands) | real `loop.json`, no `verified_at`, round-2 PASS report present | `phase=V action=verify round=1` | ✅ — the exact dogfooding bug is gone (it printed `phase=E action=done` before T34) |
| Fresh PASS | `verified_at == HEAD` | `phase=E action=done` | ✅ |
| **Amended commit** | `git commit --amend --no-edit` after the PASS | `phase=V action=verify round=2` | ✅ new SHA reopens |
| **Later commit** | one commit lands after the PASS | `phase=V action=verify round=2` | ✅ |
| **Reset restoring the verified SHA** | commit B, then `git reset --hard A` where `A == verified_at` | `phase=E action=done` | ✅ correct — the tree at `A` *is* the verified tree |
| **Detached HEAD** | `git checkout --detach A` | `phase=E action=done` | ✅ `rev-parse HEAD` is branch-agnostic |
| **No commits at all** | fresh `git init` | `_gitio.head_commit` → `None`; `_verification_covers_head` → `False` for `verified_at` ∈ {`None`, missing `verify`, `verify=None`, `""`, `"abc"`} | ✅ no `None == None` false positive — the `verified_at is None` early return fires first (`scripts/detect_phase.py:73-74`) |
| **Not a repository** | root outside any repo | `head_commit` → `None` → `False` | ✅ |
| **Stale PASS at the configured ceiling** | `rounds=3`, `max_rounds=3`, `verified_at != HEAD` | `phase=H action=halt reason=verify_exhausted` | ✅ bounded escalation (detail text quibble in §6, O2) |
| **PASS covering HEAD at the ceiling** | `rounds=3`, `max_rounds=3`, `verified_at == HEAD` | `phase=E action=done` | ✅ a PASS is not a halt |

**Two residual paths where a stale tree still reaches `phase=E`** — both are *uncommitted*-change variants, which the check by construction cannot see (it compares SHAs, not content):

| Attack | Line printed | Assessment |
| --- | --- | --- |
| Dirty worktree at the verified commit (`SKILL.md` edited, uncommitted) | `phase=E action=done` | Out of T34's remit. The spec's remedy for this is a **prose** halt: `spec.md:221` + `references/recovery-loop.md:96` ("Uncommitted changes map to no current task → halt with `phase=H reason=blocker`"), already recorded as prose-only in round 2 |
| `git reset --soft` back to the verified commit, index still holding the newer content | `phase=E action=done` | Same class |

Recorded as Observation O1, not a gap: no AC assigns this to the detector.

### 3.2 `detect_phase.py` must remain side-effect free — **proven, not accepted**

`_verification_covers_head` adds a `git rev-parse HEAD` subprocess to a script whose read-only property is LOOP-01 AC 6. The in-suite assertions (`scripts/test_unit_detect_phase.py:633-646`, `:336-343`, `:409-416`) all exercise the `phase=B` path, which returns at step 5 and **never reaches** the new call. So I proved it independently: a whole-tree snapshot of every file under the project root — including everything inside `.git` — by SHA-256 content hash, byte size and `st_mtime_ns`, taken before and after each run.

| Path exercised | Line emitted | Files added | removed | changed |
| --- | --- | --- | --- | --- |
| `phase=V` (step 6 reached, coverage check runs, real sibling `validate_state.py` invoked as a subprocess) | `phase=V action=verify round=1` | 0 | 0 | 5 × `scripts/__pycache__/*.pyc` only (interpreter bytecode cache, `.gitignore`d) |
| Same command, second run (cache settled) | identical line | 0 | 0 | **0** |
| `phase=E` (coverage check returns True, sibling validator invoked) | `phase=E action=done` | 0 | 0 | **0** |

Nothing is written on either branch, including the one that shells out to the sibling validator, and the output is idempotent across repeated runs. `_gitio.head_commit` uses `git rev-parse HEAD`, which does not touch the index.

### 3.3 Does the absent-`verified_at` branch strand a run?

Traced through `scripts/detect_phase.py:244` → `:256` → `:262-265` and confirmed by execution:

- **`max_rounds` unset (the default; `_config.defaults()` at `scripts/_config.py:56` makes it `None` = unlimited).** Detect prints `phase=V action=verify round=1`. The agent runs the round and records it (`SKILL.md:239-244`, step 4, mandatory; `references/checklist.md:91`), which stamps `verified_at = HEAD` (`scripts/update_loop.py:153`). The very next detect prints `phase=E action=done`. **Verified by execution — exactly one extra round, then it escapes.** Not a strand.
- **`max_rounds` set.** The ceiling is checked at `:256`, ahead of both round-dispatching phases, so the loop halts `verify_exhausted` at the budget. Bounded.
- **Liveness caveat.** If the agent writes the report but never calls `update_loop.py --verify-round`, `rounds` never advances and `verified_at` is never stamped, so detect prints `phase=V` forever. Before T34 that misuse terminated at `phase=E`. With a fully default config nothing bounds it: every `[limits]` key defaults to unlimited (D8, `scripts/_config.py:25-32`), `loop.sh` is an uncapped `while :;` (`scripts/loop.sh:114`) that terminates only on `phase=E`/`phase=H` or a failing respawn, and `loop.sh` never invokes `update_loop.py` at all. The safeguard is entirely prose. Recorded as Observation O3, not a gap: the recording step is mandated in two places and no AC requires a code-level bound.

### 3.4 Backward compatibility of the schema change

`verified_at` was added to `new_state` (`scripts/_state_io.py:68-69`) but **not** to `REQUIRED_KEYS`, and `_validate` only checks that `verify` is a dict (`:91-93`). A `loop.json` written before `c7d4cfe` therefore still loads — confirmed against this repository's own live `loop.json`, whose `verify` block has no `verified_at` and which `detect_phase.py` reads without error. This is strictly better than the `reconciled` migration round 2 flagged as Observation 4, which did break in-flight state.

---

## 4. The four rewritten tests, the inverted characterization test, and the README claims

### 4.1 Was any assertion weakened or coverage lost?

`git diff bdacb95..HEAD -- 'scripts/test_*.py'` removes exactly **8 assertion-bearing lines**, every one of which is replaced by a stronger or equivalent form. Nothing was deleted, renamed away, or skipped.

| Removed | Replaced by | Net |
| --- | --- | --- |
| `self.write(".specs/features/toy/validation.md", PASS_REPORT)` ×2 (`test_int_end_to_end`) | `self.record_pass()` (`:394-408`) — same write **plus** a real `update_loop.py --verify-round PASS` invocation **plus** `assertEqual(recorded.returncode, 0, recorded.stderr)` at `:408` | **stronger** |
| `assertEqual(proc.returncode, 0, "the defect appears to be fixed…")` + `assertNotIn("must point backward", proc.stdout)` (`test_int_tlc_validators`) | `assertEqual(proc.returncode, 1, …)` + `assertIn("must point backward", proc.stdout)` at `scripts/test_int_tlc_validators.py:262-269` | **inverted, not weakened** |
| `write_state(verify={"rounds":3,"last_verdict":"PASS","gaps_open":0})` (`VerifyCeiling`) | same + `"verified_at": head` (`:512-513`); the assertion `assertEqual(self.line(), "phase=E action=done")` at `:516` is unchanged | precondition tightened |
| `self.write_state()` (`Done`) | `write_state(verify={"rounds":1,"last_verdict":"PASS","verified_at": self.head()})` (`:534-535`); assertion at `:537` unchanged | precondition tightened |
| `{"rounds":0,"last_verdict":None,"last_report":None,"gaps_open":0}` (`test_unit_state_io`) | same dict + `"verified_at": None` (`:43-44`); still a whole-dict `assertEqual`, so the new key is required | **tighter** |

Numstat: `+103 / −25` across four test files; test count **321 → 325 (+4)**. No `skipTest` added anywhere.

The two rewritten cases previously proved "a PASS report alone closes the feature". That behaviour deliberately no longer exists, so nothing was lost — the contract changed and the tests followed it.

### 4.2 Does the inverted characterization test discriminate?

**Yes — proven.** Sensor M10: I copied the sibling skill into the scratch, reverted the phase-attribution fix it depends on (deleted `phase_idx = None  # left the phase sections` at `~/.agents/skills/tlc-spec-driven/scripts/validate_tasks.py:161-162`, restoring the pre-fix "never leave phase mode" behaviour), and re-ran `test_int_tlc_validators` against the mutated copy:

```
AssertionError: 0 != 1 : a forward-phase dependency in the template layout must be
rejected; validator said: validate_tasks: 0 error(s), 0 warning(s) in …/tasks.md
```

The test fails, and its message names the exact regression. The real sibling was never touched — verified afterwards: `validate_tasks.py:162` still carries the reset.

### 4.3 The README's factual claims, checked one by one

| `README.md` claim | Verified how | Verdict |
| --- | --- | --- |
| `:65-66` "It prints exactly one line and writes nothing, so it is safe to run at any point" | whole-tree hash + mtime snapshot, both branches (§3.2) | ✅ true |
| **`:143-145` "Delete `.specs/features/my-feature/loop.json` mid-run and the next detect names the same next task"** | executed: the next detect prints `phase=0 action=bootstrap`. The repo's own test asserts this at `scripts/test_int_end_to_end.py:346` and `scripts/test_unit_detect_phase.py:228`. And at `phase=E`, delete + re-bootstrap now yields `phase=V action=verify round=1`, not the same answer, because `verified_at` is not reconstructible | ❌ **false — Gap 1** |
| `:92` "`[limits]` — omit a key for unlimited" | `scripts/_config.py:25-32` + `:58` (`{key: None for key in LIMIT_KEYS}`); `scripts/test_unit_config.py:69-73` asserts every limit `None` | ✅ true |
| `:151-161` halt-reason table (9 rows: `phase=E` + 8 reasons) | compared row by row against `update_loop.HALT_REASONS` (`scripts/update_loop.py:44-53`) — exact match, no missing, no invented | ✅ true today, **ungated — Gap 2** |
| `:181` "Eleven acceptance criteria are prose" | re-derived: **13** since LOOP-07 shipped two prose ACs in this same commit series | ❌ **stale — Gap 3** |
| `:18` "Python 3.11+ (stdlib only)" | `scripts/_config.py:18` imports `tomllib` (3.11+); full import set is stdlib-only | ✅ true |
| `:25-32` install + the symlink warning | `scripts/_paths.py:27` realpaths `__file__` then walks to the sibling, so a symlink whose *target* has no sibling fails — exactly as described. `../../.agents/skills/tlc-loop` from `~/.claude/skills/` resolves correctly | ✅ true |
| `:37-42` verify snippet printing `m.tlc_dir()` | `scripts/_paths.py:30-39`; executed against a relocated copy, printed the sibling path | ✅ true |
| `:101` `resolve_stage.py --validate --root . --feature …` | `scripts/resolve_stage.py:227-229` | ✅ true |
| `:104` "Supported providers: `claude`, `codex`, `cursor`" | `scripts/resolve_stage.py:53-57` | ✅ true |
| `:117` `bash scripts/loop.sh my-feature --root .` | `scripts/loop.sh:24-25`, `:56` | ✅ true |
| `:123` done-signature `__TLC_LOOP__ feature=my-feature verify=PASS` | `SKILL.md:289`; `references/checklist.md:132`; `assets/goal-condition.template.md:11` | ✅ true |
| `:174-178` "codex is not auto-detected… `--respawn codex`" | `scripts/init_loop.py:54-57` carries `claude` and `cursor` only; `:102` defines `--respawn` | ✅ true |
| `:186-189` development commands | executed; all three clean | ✅ true |

### 4.4 The same falsehood, and two more, in the agent-facing reference

`references/state-schema.md` is not just wrong in the same place as the README — it now **contradicts itself**, because T34 added a paragraph without retracting the three sentences it invalidates.

| `references/state-schema.md` | Says | Actually |
| --- | --- | --- |
| `:15-17` | "The file is a cache: everything durable in it is either reconstructible from git and `tasks.md`, or a counter that only matters to the run that is writing it." | `verified_at` is durable, is **not** reconstructible from git, and is **not** a counter — losing it flips the answer from `phase=E` to `phase=V`. Directly contradicted by the same file at `:169-173`: "It is the one verification fact git cannot supply on its own, which is why it lives here rather than being derived." |
| `:78-81` | "delete `loop.json` mid-run and the next detect still names the same next task, because progress was never stored here" | The next detect prints `phase=0 action=bootstrap`; after re-bootstrap at `phase=E` it prints `phase=V action=verify round=1` |
| `:82-83` | "The one exception is `no_diff_tasks` — the single piece of completion state git cannot express." | There are now **two**: `no_diff_tasks` and `verified_at` |
| `:11-12` | "deleting it costs the counters and the objective, never task progress" | Also costs the recorded verification (one verify round). Same wording at `SKILL.md:54-55` and `scripts/detect_phase.py:13-14` | 

This is the round-1 Gap 3 failure mode reproduced: a one-time-true sentence going stale when the code's contract moves underneath it.

---

## 5. Discrimination Sensor

**Isolation.** A temporary `git worktree` from `HEAD` (`13c155a`) under the session scratchpad for M1–M9; a disconnected `cp -R` copy of the repo plus a **copy** of the sibling skill for M10; a second copy for M11. Every mutation was applied to a scratch file and reverted in a `finally` block. Worktree removed with `git worktree remove --force` and pruned. **No `git stash` at any point.** Pre-sensor baseline of the real tree: `git status --porcelain` empty, `HEAD = 13c155a`.

**Depth**: expanded — **11 mutations**, weighted to the delta's new code (M1–M9 all target `_verification_covers_head`, `_gitio.head_commit`, or the `verified_at` write), plus M10 against the sibling regression the inverted test must catch and M11 against `head_commit`'s defensive branches.

**Test command per mutation**: `python3 -m unittest test_unit_detect_phase test_unit_state_io test_unit_update_loop test_int_end_to_end` (M1–M9, 127 tests); full Build gate for M10 and M11.

| # | File:line | Mutation | Killed? |
| --- | --- | --- | --- |
| M1 | `scripts/_gitio.py:51` | `head_commit` always returns `None` | ✅ Killed (5 failures + 1 error) — `Done.test_validate_state_exiting_zero_prints_done`, `StaleVerification.test_a_pass_covering_head_still_reaches_done`, `VerifyCeiling.test_a_pass_report_closes_the_feature_even_at_the_ceiling`, 2 e2e, driver timeout |
| M2 | `scripts/_gitio.py:51` | Payload fault: `head_commit` returns the **short** SHA instead of the full one | ✅ Killed (3) |
| M3 | `scripts/detect_phase.py:72-75` | `_verification_covers_head` always returns `True` — reinstates the exact bug T34 fixed | ✅ Killed (3) |
| M4 | `scripts/detect_phase.py:73-74` | Absent `verified_at` treated as **covered** (`return True`) | ✅ Killed (1) — `StaleVerification.test_a_report_with_no_recorded_verification_asks_to_verify` |
| M5 | `scripts/detect_phase.py:244` | Drop the `and _verification_covers_head(state, root)` conjunct | ✅ Killed (3) |
| M6 | `scripts/update_loop.py:153` | `--verify-round` stops stamping `verified_at` | ⚠️ **Killed by the Build/Full gate only** (2 failures + 1 error, **all in `test_int_end_to_end`**). Survives the **Quick** gate — 272/272 unit tests pass. T34 declares `Gate: quick`. See Gap 4 |
| M7 | `scripts/update_loop.py:153` | Payload fault: stamps the literal string `"HEAD"` instead of the SHA | ⚠️ Same — killed only by `test_int_end_to_end` |
| M8 | `scripts/detect_phase.py:75` | Equality inverted (`==` → `!=`): a fresh PASS is rejected and a stale one accepted | ✅ Killed (6 + 1) — both directions caught |
| M9 | `scripts/_state_io.py:68-69` | `new_state` loses the `verified_at` key | ✅ Killed (1) — `NewState.test_returns_the_documented_initial_shape` |
| M10 | `~/.agents/skills/tlc-spec-driven/scripts/validate_tasks.py:161-162` (**scratch copy**) | Sibling regression: revert the phase-attribution reset, restoring the defect the test used to characterize | ✅ Killed (1) — `test_the_standard_template_layout_rejects_a_forward_phase_dependency`, message names the regression |
| M11 | `scripts/_gitio.py:48-51` | Remove both defensive branches (`returncode != 0` → raise; drop `or None`) | ✅ Killed (4) — `update_loop.py` runs in non-repo tmpdirs, so the branch is genuinely exercised |

**Result**: **11/11 killed at the Build gate, 0 survived.** M6 and M7 additionally **survive the Quick gate**, which is the gate their own task declares.

**Isolation check (post-sensor)**: `git worktree list` → only `/Users/antoniofulg/.agents/skills/tlc-loop  13c155a [main]`. `git status --porcelain` → empty, byte-identical to the pre-sensor baseline. `git rev-parse HEAD` → `13c155a`. Sibling skill re-checked: `validate_tasks.py:162` still carries the reset. Real tree and real sibling never mutated.

---

## 6. Coverage holes the sensor exposed

`verified_at` appears in `scripts/test_unit_detect_phase.py` (6×) and `scripts/test_unit_state_io.py` (1×) and in **neither** `scripts/test_unit_update_loop.py` nor `scripts/test_int_end_to_end.py`. Consequences:

1. **The writer half of T34 has no unit assertion.** `scripts/update_loop.py:153` is the only line that stamps the commit, and every `detect_phase` test writes `verified_at` by hand instead of going through it. M6 and M7 confirm it: both pass the entire 272-test unit suite. T34's Done-when #3 — "The commit a verification covered is recorded by `update_loop.py --verify-round`" — is asserted only transitively, at integration level.
2. **The value is never asserted directly, anywhere.** M7 (stamping the literal `"HEAD"`) is caught only because the *effect* is wrong end to end. The payload/conjunction rule is satisfied behaviourally but there is no `assertEqual(state["verify"]["verified_at"], head)` in the suite.
3. **`_gitio.head_commit` has no dedicated test.** `grep -n head_commit scripts/test_*.py` returns nothing, against a Test Coverage Matrix (`tasks.md:22`) that requires support modules to cover "All branches". M11 shows the branches are exercised transitively, so this is minor — but the function was added without a home in `test_unit_gitio.py`.

---

## 7. Ranked Gaps

### Gap 1 (Major) — `README.md` and `references/state-schema.md` describe behaviour the code does not have

- **Where**: `README.md:143-145`; `references/state-schema.md:15-17`, `:78-81`, `:82-83` (and, as incompleteness rather than falsehood, `:11-12`, `SKILL.md:54-55`, `scripts/detect_phase.py:13-14`).
- **Root cause**: T34 made `loop.json` carry one fact git cannot rebuild (`verified_at`) and added a paragraph saying so at `state-schema.md:169-173`, without retracting the three earlier sentences that assert the opposite. T35 then restated one of them in the README. Separately, "the next detect names the same next task" was already wrong about the bootstrap step before T34.
- **Evidence it is false**: executed — delete → `phase=0 action=bootstrap`; re-bootstrap at `phase=E` → `phase=V action=verify round=1`. The repo's own tests assert the first half at `scripts/test_int_end_to_end.py:346` and `scripts/test_unit_detect_phase.py:228`.
- **Fix**: four sentences. State that a delete costs a bootstrap **and** the recorded verification; change "the single piece of completion state git cannot express" to name both `no_diff_tasks` and `verified_at`; reword the cache paragraph at `:15-17` to match `:169-173`.
- **Priority**: Major — this is agent-facing contract prose in a skill whose product is prose, and it is the exact failure mode of round-1 Gap 3.

### Gap 2 (Major) — the README's halt-reason enumeration is a third copy with no parity gate

- **Where**: `README.md:151-161` vs `scripts/update_loop.py:44-53`; `scripts/test_unit_docs_parity.py:34-37` (`ENUMERATIONS` covers `SKILL.md` and `references/phase-transitions.md` only).
- **Root cause**: T35 added a fourth enumeration of the halt vocabulary without registering it with the parity test that exists precisely because a hand-checked enumeration goes stale. It is accurate today; nothing keeps it accurate.
- **Fix**: one tuple entry in `ENUMERATIONS` plus whatever anchor phrase the README table needs (the existing `documented_reasons` helper already fails loudly when an anchor vanishes).
- **Priority**: Major — round-1 Gap 3 was this identical drift, and T33's stated purpose was to make it impossible.

### Gap 3 (Minor) — `README.md:181` states a prose-AC count that is stale

- **Where**: `README.md:181` — "Eleven acceptance criteria are prose".
- **Evidence**: re-derived count is **13** (§2). LOOP-07's two ACs shipped as prose in `0689638`, four commits before the README.
- **Fix**: one number, or drop the number and say "several".
- **Priority**: Minor.

### Gap 4 (Major) — T34's writer is invisible to the gate T34 declares

- **Where**: `scripts/update_loop.py:153`; `scripts/test_unit_update_loop.py` (no `verified_at` anywhere); `tasks.md` T34 `**Gate**: quick`.
- **Evidence**: mutants M6 and M7 pass all 272 unit tests (`python3 -m unittest discover -s scripts -p 'test_unit_*.py'` → OK) and die only under `test_int_end_to_end`.
- **Fix**: one unit test in `scripts/test_unit_update_loop.py` — run `--verify-round PASS` in the tmpdir repo and `assertEqual(state["verify"]["verified_at"], <HEAD sha>)`. That also closes hole 2 in §6 (the value is never directly asserted). Optionally a small `head_commit` case in `test_unit_gitio.py`, and raise T34's declared gate to `full`.
- **Priority**: Major — a surviving mutant at the declared gate level is exactly what validate.md says must become a fix task.

---

## 8. Observations (not gaps; no AC is unmet)

**O1. Staleness is SHA-only, so a dirty tree at the verified commit still reaches `phase=E`.** Demonstrated for an uncommitted edit and for `git reset --soft` back to the verified commit. The spec assigns this case to a prose halt (`spec.md:221`, `references/recovery-loop.md:96`), already recorded as prose-only. If it is ever worth closing in code, `git status --porcelain` being non-empty is the check.

**O2. The `verify_exhausted` detail can misdescribe the situation.** With a stale PASS at the ceiling the line reads `detail="3 verify round(s) without a PASS, max_rounds 3"` (`scripts/detect_phase.py:257`) — but a PASS *was* reached; it simply no longer covers HEAD. The halt itself is correct; the sentence is not.

**O3. Nothing in code bounds the "agent forgot to record the round" loop.** Before T34 a PASS report alone terminated the run; now it does not. With a default config every limit is unlimited, and `scripts/loop.sh:114` is an uncapped `while :;` that never calls `update_loop.py`. The safeguard is `SKILL.md:239-244` step 4 plus `references/checklist.md:91`, both prose.

**O4. Round-2 Observations 1–3 are still open**: `dup=` is never named in `SKILL.md` and never recorded durably; `--reconciled` has no `references/checklist.md` box; `loop.sh` parsing of advisory-bearing terminal lines has no test.

**O5. `README.md` is not covered by any row of the Test Coverage Matrix** (`tasks.md:26` names `SKILL.md`, `references/`, `assets/`). The intent — prose, build gate only — is obvious, but the matrix should name it now that the file exists.

---

## 9. Payload / Conjunction Rule

Checked for every named field in a returned object or written file across the delta.

- `update_loop.py --reconciled` — all three fields asserted on value: `task`, `winner`, `at` (`scripts/test_unit_update_loop.py:254-256`).
- `update_loop.py --verify-round` — `rounds` and `last_verdict` asserted; **`verified_at` is asserted only through its effect** (`scripts/test_int_end_to_end.py:414`, `:426`). Behaviourally sound (M7 dies), but no direct value assertion exists. Gap 4.
- `_state_io.new_state` — whole initial shape asserted field by field (`scripts/test_unit_state_io.py:32-49`), including `verified_at: None` at `:44` and the deliberate absence of `completed_tasks` at `:55`.
- `detect_phase.py` — the **complete line** is compared, not a substring, wherever the shape is deterministic (`:297`, `:372-375`, `:432-436`, `:537`, `:569`, `:576`, `:583`). Advisory-field ordering is pinned as part of the whole-line comparison.
- `checkpoint.py` — trailer values read back out of git (`:206`, `:211`), the message handed to `check_commit.py` compared byte for byte (`:184`), committed file list asserted (`:297`, `:303`, `:310`, `:340`).
- `test_unit_docs_parity.assert_parity` — the failure **message** must name the offending reason and must *not* name innocent ones (`:106-107`).

---

## 10. Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ stdlib only; no dependency added; T34 is +31 non-test lines across four files |
| Surgical changes | ✅ T34 and T26 each declare the expansion of their `Where` inline with the reason; both match the files actually touched |
| No scope creep | ✅ out-of-scope items in `spec.md:28-37` respected; T35's README deviation from the no-README doctrine is recorded as D15 in `context.md:423-440` |
| Matches patterns | ✅ `verified_at` rides the existing `verify` block; `head_commit` mirrors `is_git_repo`'s shape exactly |
| Spec-anchored outcome check | ✅ for all 25 code-realizable ACs; the 1 precision gap is flagged, not silently passed |
| Per-layer Coverage Expectation met | ⚠️ **No** — `_gitio.head_commit` (support module, "All branches") has no test in `test_unit_gitio.py`, and `update_loop.py:153` (CLI entrypoint, "Every printed output variant and every non-zero exit path") has no unit coverage. Gap 4 |
| Every test maps to a spec requirement | ✅ every new class carries a docstring naming its task and AC (`StaleVerification` → T34/LOOP-04); `record_pass` documents why it exists; no unclaimed tests |
| Documented guidelines followed | ✅ none exist — strong defaults applied (stdlib `unittest`, tmpdir-scoped, zero dependencies), as recorded in `tasks.md:18` |
| Prose matches code | ❌ **No** — Gaps 1–3 |
| No assertion weakened or test removed | ✅ 8 lines removed, all replaced by stronger or inverted forms; +4 tests; zero skips |
| Hook bypass | ✅ `--no-verify` absent from `checkpoint.py`, asserted at `scripts/test_unit_checkpoint.py:394` |

---

## 11. Edge Cases (`spec.md:218-226`)

| Edge case | Evidence | Handled? |
| --- | --- | --- |
| Not a git repository → halt at bootstrap | `scripts/test_unit_init_loop.py:142-143` — non-zero exit + `assertIn("git", proc.stderr.lower())` | ✅ |
| `tasks.md` missing or fails `validate_tasks.py` → refuse, report errors | `scripts/test_unit_init_loop.py:148-149`, `:154-155` (`assertIn("validate_tasks", proc.stderr)`); `:166` — no state written | ✅ |
| Duplicated `Task:` trailer → completed once **and** record the ambiguity | Counted once: `scripts/test_unit_gitio.py:122-124`. Surfaced: `scripts/test_unit_detect_phase.py:372-375`, `:389`, `:402`, `:432-436` | ✅ |
| Uncommitted changes mapping to no task → halt and ask | `references/recovery-loop.md:96`, `:149` (prose; no worktree check in `detect_phase.py` — see O1) | 📄 Prose-only |
| Executor commits despite the ban → keep phase open, preserve work | `references/executors.md:20-30`; `references/checklist.md:74-76` | 📄 Prose-only |
| Batch worker reports a task failure → do not start the next batch | `SKILL.md:225-226`; `references/recovery-loop.md` | 📄 Prose-only |
| `.specs/loop.config.toml` absent → run on documented defaults | `scripts/test_unit_config.py:32-47` — the whole default tree asserted key by key; `:69-73` — every limit `None`; `scripts/test_unit_init_loop.py:187` — bootstrap succeeds with no config | ✅ |
| Configured provider CLI not installed → halt with the missing command named | `references/executors.md:205-206`, `:223` (prose). No `shutil.which` check in `resolve_stage.py`; `scripts/loop.sh:157-158` surfaces the non-zero exit but does not name it as a missing command | 📄 Prose-only |

---

## 12. Gate Check

- **Gate command** (Build, from `tasks.md:36`): `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Result**: **325 passed, 0 failed, 0 skipped** (exit 0). Run twice — before the sensor and again after the scratch was discarded — with identical results.
- **Test count at round 2**: 321 · **now**: 325 · **delta**: **+4** (`StaleVerification` ×3, `test_a_commit_after_the_pass_reopens_verification` ×1)
- **Test count before the feature**: 0 — `12bd8c3` is the planning-docs commit of a greenfield repository
- **Skipped tests**: none. `test_int_tlc_validators` and `test_int_end_to_end` skip only when the sibling skill is absent; it is installed at `~/.agents/skills/tlc-spec-driven/`, so both ran against the real validators.
- **Failures**: none. `compileall` and `bash -n scripts/loop.sh` both clean.
- **Quick gate**: 272 passed, 0 failed — but see Gap 4 for what it cannot see.

---

## 13. Requirement Traceability Update

| Requirement | Current Status in `spec.md` | Proposed |
| --- | --- | --- |
| LOOP-01 | Verified | ✅ Verified (all 6 ACs asserted; unchanged this round) |
| LOOP-02 | Verified | ✅ Verified (AC 5 prose-only; unchanged this round) |
| LOOP-03 | Verified | ⚠️ Documented only — no executable evidence, by the approved coverage matrix. `spec.md:237` overstates this as "Verified" |
| LOOP-04 | Verified | ✅ Verified — **strengthened this round** by T34; AC 5 now the best-covered criterion in the spec (7 assertions across unit and integration) |
| LOOP-05 | Verified | ✅ Verified (AC 2 spec-precision gap, correctly declared; AC 6 prose-only) |
| LOOP-06 | Verified | ✅ Verified (AC 1–2 prose-only) |
| LOOP-07 | Implementing (pending verification) | ⚠️ **Delivered, prose-only, unpinned** — both ACs satisfied by text in an unversioned sibling outside the diff surface and outside the gate. Verified by reading, not by a test |

---

## 14. Summary

**Overall**: ⚠️ Issues — not ready to publish as-is; ready after four small edits.

**Spec-anchored check**: 25/39 ACs matched the spec-defined outcome with a `file:line` assertion · 13 prose-only · 1 spec-precision gap (declared) · **0 unevidenced**
**Sensor**: 11/11 mutations killed at the Build gate · 2 (M6, M7) survive the Quick gate their task declares
**Gate**: 325 passed, 0 failed, 0 skipped
**Report**: this file

**What works.** T34 is a real fix, not a paper one. The bug it targets is reproducible — before it, this repository's own `detect_phase` printed `phase=E action=done` against a report written two commits earlier; after it, the same command prints `phase=V action=verify round=1`. I attacked the check from five angles (amend, later commit, reset-to-verified-SHA, detached HEAD, empty repository) plus the verify-ceiling interaction, and it answered correctly every time, with no false positive available through any `None`/empty/missing combination. `detect_phase.py` remains provably inert with the new `git rev-parse` in place — zero files added, removed, or changed across a whole-tree content-and-mtime snapshot on both the `phase=B` and `phase=E` paths, the latter while invoking the real sibling validator. The absent-`verified_at` branch costs exactly one verify round and then escapes, verified by execution. The four rewritten tests tightened their preconditions without touching an assertion, and the inverted characterization test discriminates: reverting the sibling's phase-attribution fix in a scratch copy fails it with a message naming the regression.

**What fails.** The prose moved out of step with the code. `references/state-schema.md` now contradicts itself — `:15-17` and `:82-83` say `loop.json` holds nothing git cannot rebuild, `:169-173` says `verified_at` is exactly that — and `:78-81`, echoed at `README.md:143-145`, promises behaviour that neither the code nor the repo's own tests produce. The README added a fourth copy of the halt vocabulary outside the parity test built to stop that vocabulary drifting, and states a prose-AC count that its own commit series made stale. And the sensor found that T34's writer half is invisible to the gate T34 declares: strip the `verified_at` stamp from `update_loop.py` and all 272 unit tests still pass.

**Next steps.** Route Gaps 1–4 to a fix round: three prose edits (four sentences in `state-schema.md`, one paragraph in `README.md`, one number), one `ENUMERATIONS` entry, one unit test in `test_unit_update_loop.py`. Re-verify. This is round 3 of 3, so if the fix round does not close them, escalate to the user rather than opening a fourth. Also correct `spec.md:237` (LOOP-03 is documented, not verified) and `spec.md:241` (LOOP-07 delivered, prose-only, unpinned).
