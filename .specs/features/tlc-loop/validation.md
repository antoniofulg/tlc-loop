# tlc-loop Validation

**Date**: 2026-08-08
**Round**: **4** — the bounded final round. Round 1 FAIL → T31–T33; round 2 PASS at `bdacb95`; round 3 FAIL with four ranked gaps; T36 (`a7d1460`) claims to close all four.
**Spec**: `.specs/features/tlc-loop/spec.md`
**Diff range**: full surface `12bd8c3..HEAD` (HEAD = `a7d1460`, 46 commits). Fix-round surface: `a7d1460`. Test-regression surface: `bdacb95..HEAD`.
**Verifier**: independent sub-agent, round 4 — did not write the code, did not write the round-1/2/3 reports. Coverage re-derived from `spec.md` from scratch; every prior conclusion, including the counts, was treated as a claim to re-test rather than a fact to inherit.
**Working tree**: read-only throughout. Pre-sensor `git status --porcelain` was empty; post-sensor it is empty. All mutations ran in throwaway copies under the session scratchpad, since discarded.

---

## Verdict

**Result: FAIL** — one Major gap, carried forward from round 3 Gap 1 and only partially remediated.

Three of the four round-3 gaps are genuinely and demonstrably closed. I re-ran each of them myself rather than reading the fix:

- **Gap 2 (README halt vocabulary) — CLOSED.** The parity entry is live *and* discriminating: three separate mutations of the README table were killed, each naming the reason and the document.
- **Gap 3 (stale prose-AC count) — CLOSED.** I re-derived the count independently from `spec.md` under evidence-or-zero and got **13**, which is what `README.md:184` now says.
- **Gap 4 (T34's writer invisible to its own gate) — CLOSED.** Both mutations round 3 named — stripping the `verified_at` stamp, and stamping a fixed wrong value — now fail the **Quick** gate, not merely the Build gate.

**Gap 1 is not closed.** T36 fixed the three sentences round 3 cited by `file:line` and stopped there. The same false claim survives verbatim in **four more places**, one of them a runtime-facing reference document and one of them a source docstring:

| Location | Surviving text | Status |
| --- | --- | --- |
| `references/state-schema.md:11-12` | "It is also disposable: deleting it costs the counters and the objective, never task progress." | ❌ Two fields, and T36 established there are at least three |
| `references/phase-transitions.md:31-32` | "…why deleting `loop.json` costs counters and the objective but never task progress." | ❌ Same claim, agent-facing runtime doc |
| `references/phase-transitions.md:155-158` | "An **absent** `loop.json` costs counters and the objective, never task progress… Reconstruction is safe because nothing was lost that git does not already hold." | ❌ Provably false — see §2.1 |
| `scripts/detect_phase.py:13-14` | "deleting `loop.json` costs counters and the objective, never task progress" | ❌ Same claim, in the source |
| `.specs/features/tlc-loop/design.md:63-64` | "Deleting `loop.json` costs counters and the objective, never task progress." | ❌ Same claim, in the published planning record |

And the sentence T36 *did* rewrite introduced a new self-contradiction:

```
state-schema.md:84   Three fields are not reconstructible and are lost with the file: `objective`
state-schema.md:85   (re-supplied at bootstrap), the `counters`, and `verify.verified_at` - so a
state-schema.md:86   rebuilt state owes one verification round. Deleting the file costs those, never
state-schema.md:87   task progress.
state-schema.md:88
state-schema.md:89   The first of the three is `no_diff_tasks`, below - the piece of completion
state-schema.md:90   state git cannot express.
```

`no_diff_tasks` is not one of the three named. It is a **fourth** non-reconstructible field, and the same file documents it at `:123-131` as exactly that. The round-4 brief asked me to "confirm `state-schema.md` no longer contradicts itself about which fields git can rebuild." It does — in three different ways: `:11-12` says two fields, `:84` says three, `:89` calls a fourth one "the first of the three."

This is not a wording nit. **I ran it.** §2.1 shows a task completed via the `--no-diff` path being silently re-dispatched after `loop.json` is deleted. "Task progress lives in git, so it survives" (`README.md:146`) and "never task progress" (five locations) are claims the code cannot honour.

The project's own recorded lesson **L-005**, added by T36 in this very commit, reads: *"When a change makes a cached file hold a fact that cannot be rebuilt from source, retract **every** sentence that calls the file disposable; adding a new paragraph does not withdraw the old one."* T36 wrote that lesson and then did not apply it. This repository is about to be published; a first-time reader who greps `disposable` finds five surviving contradictions of the one paragraph that is correct.

Everything else is in good order. The gate is green at **333 passed / 0 failed / 0 skipped**, the sensor killed **8/8**, **25/39** ACs carry a `file:line` assertion whose asserted value matches the spec-defined outcome, **13** are prose-only by approved design, **1** is a declared spec-precision gap, and **0** are unevidenced.

---

## 1. Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1–T33 | ✅ Done | Unchanged from rounds 1–3. T14 remains a declared partial (codex environment marker UNRESOLVED, recorded rather than guessed — `scripts/init_loop.py` carries `claude` and `cursor` only) |
| T34 | ✅ Done | `c7d4cfe` — stale-verification refusal. Re-attacked this round; holds |
| T35 | ✅ Done | `13c155a` — README |
| T36 | ⚠️ **Partial** | `a7d1460` — closes gaps 2, 3, 4 outright. Gap 1 closed at the three cited sites only; four further copies untouched and one new contradiction introduced (`references/state-schema.md:89`) |

Live against this repository: `_gitio.completed_tasks('.')` returns 36 unique ids (T1–T36), 0 duplicates, 0 empty entries. `detect_phase.py tlc-loop --root .` prints `phase=V action=verify round=1` — no pending work, verification owed, which is exactly this round.

---

## 2. The four round-3 gaps, re-tested

### 2.1 Gap 1 — the false delete-and-resume claim — ❌ **PARTIALLY CLOSED**

**What I ran.** A throwaway copy of the repository, with `tasks.md` present and git history rewound to a mid-feature commit, driven by the real (unmutated) scripts with `--root` pointed at the copy:

| Step | Command | Output |
| --- | --- | --- |
| A1 | `detect_phase.py tlc-loop --root <scratch>` | `phase=B action=execute_batch batch=P5+P6 tasks=T20,T21,T22,T23,T24 reconciled=…` |
| A2 | `rm loop.json; detect_phase.py …` | `phase=0 action=bootstrap` |
| A3 | `init_loop.py … --objective "a DIFFERENT objective"; detect_phase.py …` | `phase=B action=execute_batch batch=P5+P6 tasks=T20,T21,T22,T23,T24 reconciled=…` |
| A4 | read back `objective` | `a DIFFERENT objective` — the original was not restored |

So the corrected wording is accurate **for git-backed task progress**, in all three places round 3 cited:

| Site | Claim | Verdict |
| --- | --- | --- |
| `README.md:144-148` | "the next detect prints `phase=0 action=bootstrap`, and once you re-bootstrap it names the same task it would have" | ✅ matches A2/A3 |
| `references/state-schema.md:80-82` | "delete `loop.json` mid-run and the next detect prints `phase=0 action=bootstrap`; re-bootstrap and it names the same task" | ✅ matches A2/A3 |
| `spec.md:81` | "confirm the loop asks to bootstrap rather than failing; re-bootstrap, and confirm the next detect names the same task git history implies" | ✅ matches A2/A3 |

**What still fails.** The blanket half of the claim — "never task progress" — is false. Continuing in the same scratch:

| Step | Command | Output |
| --- | --- | --- |
| B1 | `update_loop.py … --task-done T20 --no-diff` | `updated feature=tlc-loop iteration=0 status=active` |
| B2 | `detect_phase.py …` | `phase=B … tasks=T21,T22,T23,T24,T25,T26` — T20 correctly dropped |
| B3 | `rm loop.json; init_loop.py …; detect_phase.py …` | `phase=B … tasks=T20,T21,T22,T23,T24` — **T20 is back** |

The mechanism is `scripts/detect_phase.py:187` — `done = set(committed) | set(state.get("no_diff_tasks") or [])`. `no_diff_tasks` is written only into `loop.json` (`scripts/update_loop.py:125-128`), is required by LOOP-02 AC 6, and is not derivable from git *by construction* — that is the whole reason the field exists. Deleting `loop.json` therefore costs task progress, and the loop silently re-runs a completed task.

Five locations still assert the opposite; they are listed in the Verdict table above. Two of them are worse than stale:

- `references/phase-transitions.md:157-158`: *"Reconstruction is safe because nothing was lost that git does not already hold."* This is the doc an agent reads to decide whether reconstruction is safe. It is false for two fields.
- `references/state-schema.md:89`: *"The first of the three is `no_diff_tasks`"* — names a field that is not in the list of three immediately above it, and that the same file classifies at `:123-131` as "the one piece of completion state git cannot express."

**Also noted, not counted as a separate gap:** `scripts/test_unit_detect_phase.py:217` is named `test_deleting_the_state_file_costs_no_task_progress`. Its fixture has no `--no-diff` task, so the assertion is sound; the *name* restates the over-broad claim and will read as a guarantee to the next maintainer.

### 2.2 Gap 2 — ungated fourth copy of the halt vocabulary — ✅ **CLOSED**

`scripts/test_unit_docs_parity.py:35-39` now carries a per-document terminator, and `README.md` is entry three with `("README.md", "| Reason | Meaning |", "\n\n")`. The live test is `:95-99`.

Presence is not the bar; discrimination is. Three mutations of the README's halt table in a scratch copy, each run against `python3 -m unittest scripts.test_unit_docs_parity`:

| Mutation | Result | Failure message |
| --- | --- | --- |
| M1 — rename `no_progress` → `no_progres` in the table (`README.md:157`) | ✅ Killed | `README.md does not document halt reason(s) the code implements: no_progress` |
| M2 — delete the `verify_exhausted` row | ✅ Killed | `README.md does not document halt reason(s) the code implements: verify_exhausted` |
| M3 — delete the whole halt table | ✅ Killed | `README.md: the halt-reason enumeration anchored on '| Reason | Meaning |' is gone; parity can no longer be checked` |

Each failure names both the document and the reason. The extractor's `\n\n` terminator was checked against the real table: the `Meaning` column's backticked `loop.json` and the `phase=E` row do not match `` `([a-z_]+)` `` and so do not pollute the extracted set — confirmed empirically by the unmutated test passing.

### 2.3 Gap 3 — stale prose-AC count — ✅ **CLOSED**

I re-derived the number from `spec.md` without reading round 3's derivation first, under the rule *an AC is prose-only when no executable assertion targets its spec-defined outcome*. Full table in §3. Result: **39 total** = 25 ✅ + 13 📄 + 1 ⚠️ + 0 ❌. `README.md:184` says "Thirteen acceptance criteria are prose." Match.

Two classifications I checked rather than assumed, because they are the ones that move the number:

- **LOOP-06 AC 2** (print the literal done-signature). `grep -rn "__TLC_LOOP__"` over the whole repo returns seven hits, all in prose (`SKILL.md:289`, `README.md:123`, `references/checklist.md:132`, `assets/goal-condition.template.md:11,25,67`, `assets/iteration-summary.template.md:36`, `design.md:426`) and **zero** in any test. Prose-only, confirmed.
- **LOOP-06 AC 9** counted ✅ rather than 📄, because its spec-defined outcome (`reason=blast_radius`) *is* asserted at `scripts/test_unit_detect_phase.py:592`; only the surrounding wait discipline is prose. Applying the same rule to AC 1 puts AC 1 in 📄, since "re-enter detection in the same turn" has no assertion. Reclassifying either would give 12 or 14; the rule as stated yields 13 consistently.

### 2.4 Gap 4 — T34's writer invisible to its own gate — ✅ **CLOSED**

Both round-3 mutations re-run by me in a scratch copy, against the **Quick** gate `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`:

| Mutation | Quick gate | Killed by |
| --- | --- | --- |
| M4 — delete `state["verify"]["verified_at"] = _gitio.head_commit(args.root)` (`scripts/update_loop.py:153`) | ❌ 2 failures / 280 | `test_a_round_stamps_the_commit_it_covered`, `test_the_stamp_tracks_head_rather_than_a_fixed_value` (`AssertionError: None != '0702d57…'`) |
| M5 — replace it with `= "deadbeef"` | ❌ 3 failures / 280 | the two above plus `test_outside_a_repository_the_stamp_is_absent_rather_than_wrong` |

The three new tests are `scripts/test_unit_update_loop.py:342-368`. The fixed-value mutation is specifically killed by `:358-362`, which asserts the stamp *moves* with HEAD across two commits rather than merely being present — the exact weakness round 3 identified. `scripts/test_unit_gitio.py:145-169` adds four direct tests of `_gitio.head_commit`, including the two `None` paths.

---

## 3. Spec-Anchored Acceptance Criteria (re-derived, evidence-or-zero)

Legend: ✅ PASS (assertion targets the spec-defined outcome) · 📄 Prose-only (located, no executable assertion) · ⚠️ Spec-precision gap · ❌ GAP (no evidence).

All line numbers re-resolved against `a7d1460`. `test_unit_update_loop.py` shifted by up to +52 lines and `test_unit_gitio.py` by +27 when T36 inserted its helpers and tests, so round-3 citations into those two files no longer hold verbatim; the numbers below are mine.

### LOOP-01: Deterministic phase detection and resume

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — exactly one phase line before any work | one line, documented vocabulary | `scripts/test_unit_detect_phase.py:197` — `assertEqual(len(lines), 1, …)`, the gate on every `line()` call in the file; `:207` — `assertEqual(self.line(), "phase=0 action=bootstrap")` | ✅ PASS |
| AC 2 — git trailers authoritative over `loop.json` | git wins over conflicting state | `scripts/test_unit_gitio.py:91` — `assertEqual(ids, ["T2", "T1"])` (first-committed order); `scripts/test_unit_detect_phase.py:225` — the batch line is derived from git while state still claims a different `current_task`/`current_batch` | ✅ PASS |
| AC 3 — absent `loop.json` reconstructs | bootstrap, then the same next task git implies | `scripts/test_unit_detect_phase.py:225` → `:228` (`assertEqual(self.line(), "phase=0 action=bootstrap")`) → `:231` (`assertEqual(self.line(), before)`); `scripts/test_int_end_to_end.py:339,345,348` — same three steps over the real sibling layout. Independently re-run by hand in §2.1 | ✅ PASS |
| AC 4 — unparseable `loop.json` halts `state_corrupt` | `phase=H reason=state_corrupt`, no reconstruction | `scripts/test_unit_detect_phase.py:671` — `assertTrue(self.line().startswith("phase=H action=halt reason=state_corrupt "))`; `:677` — `assertIn("malformed JSON", line)`; `:697` — `assertNotIn("phase=B", self.line())` | ✅ PASS |
| AC 5 — git is truth **and** the reconciliation is recorded | git decides; durable audit record | Git decides: `scripts/test_unit_detect_phase.py:297` — whole-line `"…tasks=T1,T2,T3,T4,T5,T6 reconciled=T1"`; `:340`. Recorded on value: `scripts/test_unit_update_loop.py:279-280` — `assertEqual(entries[0]["winner"], "git")` + `assertRegex(entries[0]["at"], …)`. Idempotent re-record: `:298-300` | ✅ PASS |
| AC 6 — `loop.json` mutated only through its own script | single writer; detect writes nothing | `scripts/test_unit_detect_phase.py:638`/`:645` — state bytes + `git status --porcelain` byte-identical across a detect, repeated at `:337`/`:344` (with `reconciled=` live) and `:410`/`:417` (with `dup=` live); `scripts/test_unit_update_loop.py:154` — `assertNotEqual(proc.returncode, 0)` on an objective write | ✅ PASS |

**Independent Test (`spec.md:81`)**: executed by hand — §2.1 steps A1–A4. Passes as now worded.

### LOOP-02: Atomic checkpoint per task

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — one atomic commit with `Task:` and `Gate: <level> PASS` | trailers readable via `%(trailers:key=Task,valueonly)` | `scripts/test_unit_checkpoint.py:201` — `assertEqual(self.commit_count(), before + 1)`; `:206` — `assertEqual(self.trailer("Task"), "T7")`; `:211` — `assertEqual(self.trailer("Gate"), "build PASS")` | ✅ PASS |
| AC 2 — no passing gate, no commit | refusal; commit count unchanged | `:139-142` (gate omitted), `:146-149` (`FAIL`), `:153-156` (lowercase `pass`) — each non-zero exit + unchanged commit count | ✅ PASS |
| AC 3 — validate with `check_commit.py`, abort on non-zero | validated **before** staging; payload asserted | `:169-172` — refusal + no commit; `:177` — `assertEqual(self.staged(), [])`; `:184` — `assertEqual(fh.read(), GOOD_MESSAGE)` (the payload handed to the validator, not merely that it was called) | ✅ PASS |
| AC 4 — at most one commit per task, never batched | one commit; repeated trailer deduped or refused | `:201`; `:242`/`:247` — a message already carrying the trailers yields exactly one of each; `:261-264`, `:268-271` — a contradicting trailer refused | ✅ PASS |
| AC 5 — executor forbidden from committing; the loop checkpoints | prohibition + ownership | `references/executors.md:20`; `SKILL.md:62`; `references/checklist.md:74-76`. `grep -n executor scripts/test_*.py` finds no assertion on the prohibition | 📄 Prose-only |
| AC 6 — no file changes → record completion, no fabricated diff | `SKIP: no changes`, exit 0, no commit | `scripts/test_unit_checkpoint.py:279` — `assertIn("SKIP: no changes", proc.stdout)`; `:287` — commit count unchanged; `scripts/test_unit_update_loop.py:243` — `assertEqual(_read(root)["no_diff_tasks"], ["T4"])` | ✅ PASS |

**Edge case (`spec.md:220`) — duplicated `Task:` trailer**: counted once at `scripts/test_unit_gitio.py:122-124`; surfaced as `dup=` at `scripts/test_unit_detect_phase.py:402`. ✅ both halves.

### LOOP-03: Self-healing repair loop

Entirely agent-facing prose by approved design — the Test Coverage Matrix (`tasks.md:26`) assigns prose "none — build gate only". Under evidence-or-zero none of the five carries an executable assertion.

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
| AC 1 — fresh verifier dispatched, no prompting | author ≠ verifier | `SKILL.md:233-234`; `references/executors.md:133-135`; `references/checklist.md:80-84`. No assertion (`grep -in verifier scripts/test_*.py` → one docstring only) | 📄 Prose-only |
| AC 2 — verifier read-only over the real tree | no code/test modification | `SKILL.md:236`; `references/executors.md:136-138`; `references/checklist.md:85-87` | 📄 Prose-only |
| AC 3 — FAIL routes gaps to `fix`, then re-dispatches verify | `phase=F` on FAIL+open gaps; `phase=V` when gaps close | `scripts/test_unit_detect_phase.py:460` — `assertEqual(self.line(), "phase=F action=fix round=1")`; `:453` — `"phase=V action=verify round=2"` with `gaps_open=0`; `:543` — a FAIL report still yields `phase=F` | ✅ PASS |
| AC 4 — verify-round limit reached without PASS → halt and escalate | `phase=H reason=verify_exhausted`, checked ahead of V and F | `:485` — `assertTrue(line.startswith("phase=H action=halt reason=verify_exhausted "))`; `:502` — `assertIn("reason=verify_exhausted", line)` with `assertNotIn("phase=F", line)`; `:506` — omitted `max_rounds` never halts (`round=100`) | ✅ PASS |
| AC 5 — PASS confirmed with `validate_state.py`; non-zero = not done | `phase=E` only on exit 0, and only while the verdict covers HEAD | `:537` — `phase=E action=done` with `verified_at == HEAD`; `:569` — a commit after the PASS → `"phase=V action=verify round=2"`; `:576` — PASS covering HEAD → `phase=E`; `:585` — no recorded verification → `"phase=V action=verify round=1"`; `:516` — PASS at the ceiling covering HEAD → `phase=E`; `scripts/test_int_end_to_end.py:414`, `:426` — both against the real sibling validator | ✅ PASS |

### LOOP-05: Per-stage provider, model, and effort

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — resolve provider/model/effort, translate through the adapter table | per-provider command line | `scripts/test_unit_resolve_stage.py:76-77` — `assertIn("codex exec -m gpt-5.6-luna", line)` + `assertIn("-c model_reasoning_effort=max", line)`; `:93` — `assertIn("claude-opus-5[effort=high]", line)`; `:125-126` — `--model opus` + `--effort high` | ✅ PASS |
| AC 2 — unsupported effort rejected before dispatch | rejection names stage, provider, accepted values | `scripts/test_unit_config.py:165-166` — `assertIn("stages.verify", message)` + `assertIn("ultra", message)` (the reachable path); `scripts/test_unit_resolve_stage.py:180-181`, `:193-196` (the per-provider path, asserted directly on `check_effort`) | ⚠️ Spec-precision gap (declared — note below) |
| AC 3 — provider == running harness → native sub-agent | `kind=agent`, no CLI | `scripts/test_unit_resolve_stage.py:142` — `assertEqual(line, "kind=agent provider=claude model=opus effort=high")`; `:147` — `assertNotIn("cmd=", line)` | ✅ PASS |
| AC 4 — config read-only; runtime values recorded in `loop.json` | no write to `loop.config.toml` | `scripts/_config.py` exposes no writer; `scripts/test_unit_init_loop.py:216` — `assertEqual(self.state()["harness_resolved"], "cursor")`; `scripts/test_int_end_to_end.py:324` — `assertEqual(self.state_bytes(), before)` | ✅ PASS |
| AC 5 — launch/auth/quota failure halts with the reason recorded | `phase=H reason=executor`, resumable | `scripts/test_unit_update_loop.py:382-383` — `assertEqual(halt["reason"], "executor")` + `assertEqual(halt["detail"], "codex quota exhausted")`; `scripts/test_unit_detect_phase.py:599` — `assertIn("reason=executor", self.line())` | ✅ PASS |
| AC 6 — verify an executor's evidence before advancing | a claim without an artifact is not completion | `references/executors.md:61-71`, `:174-180`; `references/checklist.md:61-65` | 📄 Prose-only |

**⚠️ AC 2 note — re-confirmed independently for the fourth time.** `_config.EFFORTS` rejects anything outside `low/medium/high/xhigh/max` at load time; `resolve_stage.PROVIDER_EFFORTS` (`scripts/resolve_stage.py:53-57`) gives `claude` and `cursor` exactly that set and `codex` a superset, and `check_effort` returns early for a provider absent from the table. No config-legal effort can reach the per-provider rejection, so that branch is asserted on `check_effort` directly rather than end to end. `tasks.md` declares this accurately. Untouched by T36.

### LOOP-06: Unattended continuation and stop conditions

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — re-enter detection in the same turn | control not returned while non-terminal | `SKILL.md:326-329` (in-turn gate, prose); `references/checklist.md:34-36`. Cross-turn analogue asserted at `scripts/test_int_loop_sh.py:177-178` — `assertEqual(self.spawns(), 4)` + `assertEqual(self.detect_calls(), 5)` over `0→B→V→F→E`. The in-turn requirement itself has no assertion | 📄 Prose-only (in-turn) |
| AC 2 — print the literal done-signature when `validate_state.py` exits 0 | `__TLC_LOOP__ feature=<feature> verify=PASS` | `SKILL.md:289`; `references/checklist.md:132`; `assets/goal-condition.template.md:11`; `assets/iteration-summary.template.md:36`. Repo-wide grep finds the string in **no** test | 📄 Prose-only |
| AC 3 — resolve continuation from the harness, record it | `harness_resolved` in `loop.json` | `scripts/test_unit_init_loop.py:212` — `assertEqual(self.state()["harness_resolved"], "claude")`; `:216` — `"cursor"`; `:239-252` — explicit and configured `--respawn` record `"codex"` | ✅ PASS |
| AC 4 — inconclusive detection halts and asks | non-zero exit, no state written, tells the user how | `:224` — `assertNotEqual(proc.returncode, 0)`; `:228` — `assertIn("--respawn", proc.stderr)`; `:230-232` — no state file written; `:234-236` — two markers at once are also inconclusive | ✅ PASS |
| AC 5 — objective immutable for the run | verbatim at bootstrap, unwritable after | `scripts/test_unit_init_loop.py:193-200` — stored exactly as passed, punctuation intact; `scripts/test_unit_update_loop.py:166` — unchanged after a rejected write; `:172` — `assertEqual(_read(root)["iteration"], 0)`, so a rejected call applies none of its other flags | ✅ PASS |
| AC 6 — no new commit across N iterations → halt | `reason=no_progress` | `scripts/test_unit_detect_phase.py:604` — `assertIn("reason=no_progress", self.line())`; `scripts/test_unit_update_loop.py:206-208` — counter 1→2; `:217` — reset to 0 on a recorded commit; `scripts/test_int_end_to_end.py:373` | ✅ PASS |
| AC 7 — same task's gate fails more than N attempts → halt | `reason=gate_stuck`, task named | `scripts/test_unit_detect_phase.py:610-611` — `assertIn("reason=gate_stuck", line)` + `assertIn("T4", line)`; `scripts/test_unit_update_loop.py:196` — `assertEqual(…, {"T3": 2, "T4": 1})` | ✅ PASS |
| AC 8 — `max_iterations` / `max_minutes` reached → write state, halt cleanly | `reason=limit` | `scripts/test_unit_detect_phase.py:616` — `assertIn("reason=limit", self.line())`; `:625` — a `phase=B ` line when the limit is omitted | ✅ PASS |
| AC 9 — remote/destructive operation → halt and wait for authorization | `reason=blast_radius`, no proceeding | `scripts/test_unit_detect_phase.py:592-593` — `assertTrue(line.startswith("phase=H action=halt reason=blast_radius "))` + `assertIn('detail="push required"', line)`. The wait discipline itself is prose (`SKILL.md:70-77`; `references/checklist.md:143-145`) | ✅ PASS |

### LOOP-07: Handoff from tlc-spec-driven

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC 1 — Execute with a >1-batch `tasks.md` presents loop mode alongside inline and sub-agents | three options, one line each, invocation named | `~/.agents/skills/tlc-spec-driven/references/sub-agents.md:40-47` — the three-option offer block; `:44` names `` `/tlc-loop [feature]` ``. Trigger gated at `:14`. No executable assertion | 📄 Prose-only |
| AC 2 — declining falls back to existing behaviour unchanged | inline path preserved | `~/.agents/skills/tlc-spec-driven/references/sub-agents.md:48` — "The user must explicitly accept. If they decline (or if the feature fits one batch), execute inline."; `:50` — degrades to two options when `tlc-loop` is absent. No executable assertion | 📄 Prose-only |

**Durability caveat (unchanged from round 3, still open).** LOOP-07's entire deliverable lives outside this repository, in `~/.agents/skills/tlc-spec-driven`, which is not under version control. It is absent from the diff surface and from the build gate. A reinstall of `tlc-spec-driven` from upstream silently reverts LOOP-07 and nothing here notices. Recorded as Observation O4 rather than a new gap, since it is the same finding round 3 already surfaced and no AC requires pinning.

### Count (re-derived independently)

**39 criteria**: LOOP-01 ×6, LOOP-02 ×6, LOOP-03 ×5, LOOP-04 ×5, LOOP-05 ×6, LOOP-06 ×9, LOOP-07 ×2.

| Result | Count | Where |
| --- | --- | --- |
| ✅ PASS with a spec-matched assertion | **25** | LOOP-01 ×6, LOOP-02 ×5, LOOP-04 ×3, LOOP-05 ×4, LOOP-06 ×7 |
| 📄 Prose-only (located, no executable assertion) | **13** | LOOP-02 AC 5; LOOP-03 ×5; LOOP-04 AC 1–2; LOOP-05 AC 6; LOOP-06 AC 1–2; LOOP-07 ×2 |
| ⚠️ Spec-precision gap (declared) | **1** | LOOP-05 AC 2 |
| ❌ GAP (no evidence) | **0** | — |

`README.md:184` claims thirteen prose criteria. **Confirmed: 13.**

---

## 4. Edge Cases (`spec.md:218-226`)

| Edge case | Evidence | Result |
| --- | --- | --- |
| Not a git repository → halt at bootstrap | `scripts/test_unit_init_loop.py:136-143` — non-zero exit + `assertIn("git", proc.stderr.lower())`; `scripts/test_unit_gitio.py:137-142` | ✅ |
| `tasks.md` missing or failing `validate_tasks.py` → refuse and report | `scripts/test_unit_init_loop.py:145-149` (`assertIn("tasks.md", proc.stderr)`), `:151-155` (`assertIn("validate_tasks", proc.stderr)`); `scripts/test_int_tlc_validators.py:192+` against the real validator | ✅ |
| Duplicated `Task:` trailer → completed once, ambiguity recorded | `scripts/test_unit_gitio.py:122-124`; surfaced as `dup=` at `scripts/test_unit_detect_phase.py:402` | ✅ |
| Uncommitted changes mapping to no task → halt and ask | `references/recovery-loop.md:96`, `:149` (prose; no worktree check in `detect_phase.py`) | 📄 Prose-only |
| Executor commits despite the prohibition → keep phase open, preserve work, do not advance | `references/executors.md:20`; `references/checklist.md:74-76` (prose) | 📄 Prose-only |
| Batch worker reports a failure → next batch does not start | `SKILL.md`/`references/checklist.md` (prose) | 📄 Prose-only |
| `.specs/loop.config.toml` absent → documented defaults | `scripts/test_unit_config.py:69-98` — every limit unlimited, stage defaults intact; `scripts/test_unit_init_loop.py:186` | ✅ |
| Configured provider CLI not installed → halt with the missing command named | `references/executors.md:205-206`, `:223` (prose). No `shutil.which` check in `resolve_stage.py` | 📄 Prose-only |

---

## 5. Discrimination Sensor

**Isolation.** Temp copies of the repository under the session scratchpad, with a symlinked sibling `tlc-spec-driven` so path resolution behaved as installed. No `git stash`; the real worktree was never written. Pre-sensor `git status --porcelain` was empty; post-sensor it is empty, and `git rev-parse HEAD` is still `a7d1460`. Scratch discarded.

**Depth**: expanded (8 mutations) — the feature drives unattended commits, so `checkpoint`/`update_loop`/`detect_phase` are treated as data-integrity paths.

| # | File:line | Mutation | Gate run | Killed? |
| --- | --- | --- | --- | --- |
| M1 | `README.md:157` | Rename `no_progress` → `no_progres` in the halt table | `test_unit_docs_parity` | ✅ Killed — names `no_progress` and `README.md` |
| M2 | `README.md:161` | Delete the `verify_exhausted` row | `test_unit_docs_parity` | ✅ Killed — names `verify_exhausted` |
| M3 | `README.md:154-164` | Delete the whole halt table | `test_unit_docs_parity` | ✅ Killed — "the enumeration anchored on '\| Reason \| Meaning \|' is gone" |
| M4 | `scripts/update_loop.py:153` | Remove the `verified_at` stamp entirely | **Quick** (280 tests) | ✅ Killed — 2 failures |
| M5 | `scripts/update_loop.py:153` | Stamp a fixed wrong value `"deadbeef"` | **Quick** (280 tests) | ✅ Killed — 3 failures |
| M6 | `scripts/_gitio.py:51` | `head_commit` returns a 7-char abbreviation | **Quick** (280 tests) | ✅ Killed — 7 failures across `gitio`, `update_loop`, `detect_phase` |
| M7 | `scripts/detect_phase.py:73-74` | Absent `verified_at` counts as covering HEAD (`return False` → `return True`) | **Quick** (280 tests) | ✅ Killed — `test_a_report_with_no_recorded_verification_asks_to_verify` |
| M8 | `scripts/detect_phase.py:187` | Drop `no_diff_tasks` from the completed set | **Quick** (280 tests) | ✅ Killed — 2 failures |

**Result: 8/8 killed.** No surviving mutants. The two mutations round 3 reported as surviving (M4, M5 here) are now killed by the Quick gate T34 declares.

---

## 6. Gate Check

- **Gate command (Build, from `tasks.md:36`)**: `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Result**: **333 passed, 0 failed, 0 skipped**, exit 0
- **Quick gate** (`-p 'test_unit_*.py'`): **280 passed, 0 failed**, exit 0
- **Test count before T36**: 325 · **after**: 333 · **Delta**: +8
- **Skipped tests**: none
- **Failures**: none

---

## 7. Regression check on T36 (`git diff bdacb95..HEAD -- scripts/test_*.py`)

T36 touched three test files. Reviewed line by line:

| File | Change | Assessment |
| --- | --- | --- |
| `scripts/test_unit_docs_parity.py` | `ENUMERATIONS` entries gain a third element (terminator); `documented_reasons` takes `terminator=".\n"` with the old value as default; new `test_readme_enumerates_exactly_the_implemented_reasons`; `test_every_documented_enumeration_is_locatable` unpacks `*entry` instead of two names | No assertion weakened. The two pre-existing parity tests keep the identical terminator via the default; the loop test keeps its `assertTrue`. Net **+1 test** |
| `scripts/test_unit_gitio.py` | New `HeadCommit` class, 4 tests | Pure addition. Net **+4** |
| `scripts/test_unit_update_loop.py` | `_git`/`_seed_repo`/`_commit_more` helpers; 3 new tests in `VerifyRounds` | Pure addition. No existing test altered. Net **+3** |

+8 tests, matching 325 → 333 exactly. **No test deleted, no assertion loosened, no coverage lost.** The earlier `bdacb95..13c155a` portion of the range (the characterization-test inversion in `test_int_tlc_validators.py`, and the `verified_at` additions in `test_unit_detect_phase.py` / `test_unit_state_io.py`) strengthens assertions rather than weakening them — `assertEqual(proc.returncode, 0)` became `assertEqual(proc.returncode, 1)` with `assertIn("must point backward", proc.stdout)`.

---

## 8. Published-repository accuracy audit

`README.md` and `references/` are the product. Every executable or checkable claim in `README.md` was run:

| Claim | Check | Result |
| --- | --- | --- |
| `:18` Python 3.11+, stdlib only | `scripts/_config.py:18` imports `tomllib` (3.11+); no third-party imports anywhere in `scripts/` | ✅ |
| `:29-32` install + symlink recipe | `~/.claude/skills/tlc-loop → ../../.agents/skills/tlc-loop` resolves to `~/.agents/skills/tlc-loop` | ✅ |
| `:37-42` verify snippet prints the sibling path | Ran it from `/tmp`: prints `/Users/antoniofulg/.agents/skills/tlc-spec-driven` | ✅ |
| `:62` `detect_phase.py … --root .` is read-only and prints one line | Ran against this repo: one line, `git status --porcelain` unchanged | ✅ |
| `:76-95` the headline "cheap implementer + high-reasoning verifier" config | Written verbatim to a scratch `.specs/loop.config.toml` and validated: `ok 4 stage(s) resolve`, exit 0 | ✅ |
| `:101` `resolve_stage.py --validate --root . --feature my-feature` | Every flag exists in `--help` | ✅ |
| `:104` "Supported providers: `claude`, `codex`, `cursor`" | Matches `resolve_stage.PROVIDER_EFFORTS` keys (`scripts/resolve_stage.py:53-57`) | ✅ |
| `:117` `bash scripts/loop.sh my-feature --root .` | Matches the documented usage at `scripts/loop.sh:24-25` | ✅ |
| `:123` done-signature string | Byte-identical to `SKILL.md:289` and both templates | ✅ |
| `:154-164` halt table | Now gated by the parity test; 8 reasons matching `update_loop.HALT_REASONS` | ✅ |
| `:184` "Thirteen acceptance criteria are prose" | Re-derived: 13 | ✅ |
| `:190-192` development commands | All three run clean | ✅ |
| **`:144-148` delete-`loop.json` paragraph** | "Task progress lives in git, so it survives" — **false for `no_diff_tasks`** (§2.1 B1–B3) | ❌ **Gap 1** |
| `:204` "License: CC-BY-4.0" | `git ls-files` shows no `LICENSE` file at the repository root | Observation O5 |

---

## 9. Ranked Gaps

### Gap 1 (Major) — the "never task progress" claim survives in five places, and the one rewritten sentence is incoherent

- **Where**:
  - `references/state-schema.md:11-12` — "deleting it costs the counters and the objective, never task progress"
  - `references/state-schema.md:89-90` — "The first of the three is `no_diff_tasks`" (names a fourth field as one of three)
  - `references/phase-transitions.md:31-32` — same claim
  - `references/phase-transitions.md:155-158` — same claim plus "Reconstruction is safe because nothing was lost that git does not already hold"
  - `scripts/detect_phase.py:13-14` — same claim, in the module docstring
  - `.specs/features/tlc-loop/design.md:63-64` — same claim
  - `README.md:146` — "Task progress lives in git, so it survives"
  - `spec.md:81` — "Task progress survives the deletion"
- **Root cause**: T36 remediated at the three `file:line` citations round 3 supplied, rather than searching the repository for the claim. `no_diff_tasks` (LOOP-02 AC 6) is a fourth field git cannot rebuild, and it was already non-reconstructible before T34 — it is not new, only newly relevant once the paragraph started enumerating losses.
- **Evidence**: §2.1 steps B1–B3, run against the real scripts. `scripts/detect_phase.py:187` is the mechanism.
- **Fix task**: (a) In `references/state-schema.md`, make `:11-12`, `:84-90` and `:123-131` agree: four fields are lost — `objective`, `counters`, `verify.verified_at`, `no_diff_tasks` — and deleting the file costs the completion of any no-diff task. Delete or rewrite the dangling "The first of the three" sentence. (b) Apply the same correction at `references/phase-transitions.md:31-32` and `:155-158`, including the "Reconstruction is safe" sentence. (c) Correct `scripts/detect_phase.py:13-14`, `README.md:146`, `.specs/features/tlc-loop/design.md:63-64`, and `spec.md:81`. (d) Consider renaming `scripts/test_unit_detect_phase.py:217` so the test name stops restating the over-broad claim. (e) If the claim is worth keeping honest mechanically, the same trick as T33 applies: a parity test over the distinctive phrase.
- **Verify**: `grep -rn "never task progress\|costs counters\|costs the counters" --exclude-dir=.git .` returns only corrected sentences; a re-run of §2.1 B1–B3 matches whatever the prose then says.
- **Priority**: **Major** — same defect class as round-1 Gap 3 and round-3 Gap 1, in a skill whose shipped product is its prose, in a repository about to be published. The project's own lesson L-005 prescribes exactly the discipline that was not applied.

**No other gaps.** Gaps 2, 3 and 4 from round 3 are closed and were re-tested rather than accepted.

---

## 10. Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ T36 added 8 tests and edited 4 prose files; nothing speculative |
| Surgical changes | ✅ The extractor generalisation is the minimum change that lets a table be gated |
| No scope creep | ✅ |
| Only touched files required for the task | ✅ |
| Didn't "improve" unrelated code | ✅ |
| Matches existing patterns/style | ✅ |
| Would a senior engineer approve? | ⚠️ Yes for the code; no for the prose remediation — fixing only the cited lines when the claim is greppable is the defect being repeated |
| Tests map to ACs and are non-shallow | ✅ `test_the_stamp_tracks_head_rather_than_a_fixed_value` is the right shape: it defeats both the missing-stamp and the constant-stamp mutant |
| Spec-anchored outcome check | ✅ 25/25 asserted ACs target the spec-defined value |
| Per-layer Coverage Expectation met | ✅ Domain logic 1:1 with ACs; the driver has happy/edge/error paths in `test_int_loop_sh.py` |
| Every test maps to a spec requirement — no unclaimed tests | ✅ All 8 new tests map to LOOP-04 AC 5 (verified_at) and LOOP-06 (halt vocabulary parity, T33) |
| Documented guidelines followed | ✅ `tasks.md:28-38` Gate Check Commands; `references/coding-principles.md` |

---

## 11. Requirement Traceability

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| LOOP-01 | Verified | ⚠️ **Needs Fix** — code verified (6/6 ACs asserted); the AC 3 behaviour is misdescribed by five surviving prose claims and one source docstring |
| LOOP-02 | Verified | ✅ Verified (AC 5 prose-only, unchanged) |
| LOOP-03 | Verified | ✅ Documented (all five prose-only by approved design) |
| LOOP-04 | Verified | ✅ Verified — strengthened this round; AC 1–2 prose-only |
| LOOP-05 | Verified | ✅ Verified (AC 2 spec-precision gap, correctly declared; AC 6 prose-only) |
| LOOP-06 | Verified | ✅ Verified (AC 1–2 prose-only) |
| LOOP-07 | Implementing (pending verification) | ⚠️ **Delivered, prose-only, unpinned** — both ACs satisfied by text in an unversioned sibling outside the diff surface and outside the gate |

---

## 12. Observations (not gaps)

**O1. Staleness is SHA-only.** A dirty tree at the verified commit still reaches `phase=E`. The spec assigns this case to a prose halt (`spec.md:221`, `references/recovery-loop.md:96`). Unchanged from round 3.

**O2. The done-signature string is enumerated in seven documents with no parity gate.** `SKILL.md:289`, `README.md:123`, `references/checklist.md:132`, `assets/goal-condition.template.md:11,25,67`, `assets/iteration-summary.template.md:36`, `design.md:426`. This is the same drift shape T33 built the halt-vocabulary parity test to prevent, minus a code constant to anchor against. Currently all seven agree.

**O3. Nothing in code bounds the "agent forgot to record the verify round" loop.** With a default config every limit is unlimited and `scripts/loop.sh:114` is an uncapped `while :;` that never calls `update_loop.py`. The safeguard is `SKILL.md` step 4 plus `references/checklist.md:91`, both prose. Unchanged from round 3.

**O4. LOOP-07's deliverable is unversioned and outside the gate.** `~/.agents/skills/tlc-spec-driven` is not a git repository; a reinstall silently reverts the handoff and nothing here notices.

**O5. No `LICENSE` file.** `README.md:204` and `SKILL.md` both declare CC-BY-4.0, but `git ls-files` shows only `.gitignore`, `README.md` and `SKILL.md` at the root. For a repository about to be published, the license text should ship.

**O6. `README.md` is still not named by any row of the Test Coverage Matrix** (`tasks.md:26` names `SKILL.md`, `references/`, `assets/`). It is now partially gated by the parity test, which makes the omission more visible rather than less.

---

## Summary

**Overall**: ❌ **Not Ready**

**Spec-anchored check**: 25/39 ACs matched the spec-defined outcome with a `file:line` assertion · 13 prose-only (by approved design) · 1 declared spec-precision gap · **0 unevidenced**
**Sensor**: 8 mutations injected, **8 killed, 0 survived** (expanded depth)
**Gate**: 333 passed, 0 failed, 0 skipped (Build); 280 passed, 0 failed (Quick)
**Diff range**: `12bd8c3..HEAD` (`a7d1460`); fix-round surface `a7d1460`; test-regression surface `bdacb95..HEAD`
**Isolation**: pre- and post-sensor `git status --porcelain` both empty; HEAD unchanged at `a7d1460`

**What works.** The engineering is sound and has now survived four adversarial rounds. Three of round 3's four gaps are closed and I verified each by re-running the attack rather than reading the fix: the README's halt table is under a parity gate that provably fails and names the reason; the prose-AC count re-derives to 13 independently; and both `verified_at` mutations that previously slipped through now fail the Quick gate the task declares. No mutant survived, no test was weakened, no coverage was lost, and the README's every runnable claim runs.

**What fails.** Round 3's Gap 1 was remediated at its three citations and nowhere else. The claim "deleting `loop.json` costs counters and the objective, never task progress" survives in `references/phase-transitions.md` twice, `references/state-schema.md` once, `scripts/detect_phase.py`'s docstring, and `design.md` — and it is false: a task completed through the `--no-diff` path is silently re-dispatched after the file is deleted, which I demonstrated. The one sentence T36 did rewrite now reads "The first of the three is `no_diff_tasks`" about a list that does not contain it, so `state-schema.md` contradicts itself in three places rather than one. T36 recorded lesson L-005 — "retract *every* sentence that calls the file disposable" — in the same commit that failed to do so.

**Next steps.** This is round 4 and the fix→re-verify budget is spent. **Escalate to the user** rather than opening a fifth round. The remaining work is one greppable prose sweep across six files plus one incoherent sentence — cheap, but it is the last thing standing between this repository and a public README that promises behaviour the code does not have.
