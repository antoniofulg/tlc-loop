# Halt Resume Validation

## Validation: halt-resume - PASS ✅

**Round**: 2 (re-verification after the round-1 gaps were fixed)
**Date**: 2026-08-11
**Spec**: `.specs/features/halt-resume/spec.md`
**Diff range**: `main...HEAD` = `dc8161c..a8e92c6` (9 commits, branch `fix/halt-resume-transition`)
**HEAD**: `a8e92c61d14b1b09905a50b55a0b760fd0a4a7d1`
**Verifier**: independent sub-agent (author ≠ verifier), read-only over the real
tree apart from this file

**Verdict**: ✅ **PASS** — the three round-1 survivors are dead, the behaviour
layer is undiminished, and the gate is green. All 14 acceptance criteria now
match their spec-defined outcome at the scope the spec words them. Four
non-blocking precision observations are ranked at the end; none of them is a
defect in the shipped artifact, and none blocks the feature.

---

## What Changed Since Round 1

Round 1 failed on one root cause: the three P3 documentation guards asserted
`--resume` over the whole file while each acceptance criterion scopes the
requirement to a named passage. Commit `a8e92c6` is **test-only** — it touches
`scripts/test_unit_docs_parity.py` and the lessons store, and no shipped prose,
script, or behaviour:

```
.specs/LESSONS.md
.specs/features/halt-resume/validation.md
.specs/lessons.json
scripts/test_unit_docs_parity.py
```

It made three changes: scoped each P3 guard to its passage (`table_row` for the
`H` row, `section` for the two headed passages), raised the needle from the
`--resume` flag substring to the whole command form via a new `collapsed()`
helper, and fixed `section()` to end at the next heading of the same level *or
shallower*.

That last one was load-bearing and is worth recording. `#### Phase H - Halt` is
the last `####` under its parent, so a scan stopping only at the same level ran
to end of file — no scope at all. Measured on the real tree:

| Section | Old `phase_section()` | New `section()` | Effect |
| --- | --- | --- | --- |
| `SKILL.md:219` `#### Phase B` | 3624 chars | 3624 chars | identical — P2 guard unchanged |
| `SKILL.md:373` `#### Phase H` | 4722 chars (to EOF) | 1617 chars (ends before `### Step 3` at `SKILL.md:406`) | scope tightened 2.9× |

---

## Weakening Audit (was any test loosened, deleted, or skipped?)

**No.** One test was replaced by four; every replacement is strictly stronger.

| Before (`034612b`) | After (`a8e92c6`) | Stronger? |
| --- | --- | --- |
| `test_the_documents_that_describe_the_halt_name_the_flag` — one loop, `assertIn("--resume", read_shipped(relative))` over three whole files | `scripts/test_unit_docs_parity.py:383` `test_the_transition_row_names_the_flag` — same needle, scope narrowed from the whole file to the `H` row | ✅ scope ⊂ file, needle equal |
| ″ | `scripts/test_unit_docs_parity.py:396` `test_the_halt_field_section_names_the_command` — `assertIn("update_loop.py <feature> --root <root> --resume", collapsed(body))` over the `` ## `halt` `` section | ✅ scope ⊂ file **and** needle ⊃ `--resume` |
| ″ | `scripts/test_unit_docs_parity.py:406` `test_the_halt_phase_names_the_command` — same needle over the `#### Phase H - Halt` section | ✅ scope ⊂ file **and** needle ⊃ `--resume` |
| (none) | `scripts/test_unit_docs_parity.py:415` `test_each_scope_excludes_the_passage_that_follows_it` — new meta-test pinning all three scopes | ✅ pure addition |
| `scripts/test_unit_docs_parity.py:493` P2 guard: `assertIn("--gate-attempt", body)` | `assertIn("update_loop.py <feature> --root <root> --gate-attempt", collapsed(body))` | ✅ same scope (measured identical above), needle ⊃ old |

Formal check on the two `collapsed()` rewrites: if the collapsed section
contains `update_loop.py <feature> --root <root> --resume`, it contains
`--resume`; `--resume` holds no whitespace, so collapsing cannot have
manufactured it; therefore the raw section — and so the whole file — contained
it too. New passing ⟹ old passing, and the converse fails (M11b, M12). Strictly
stronger, not merely different.

**Deleted**: none. **Skipped/`expectedFailure`**: none — `grep` finds no `skip`
decorator or `expectedFailure` anywhere in `scripts/test_unit_docs_parity.py`.
**Test count**: 575 → 578 (+3 net: 1 removed, 4 added).

**Vacuous assertions**: one found, in the new meta-test.
`scripts/test_unit_docs_parity.py:431` `assertNotIn("\n", row)` can never fail —
`table_row()` (`scripts/test_unit_docs_parity.py:466-471`) returns an element of
`text.splitlines()`, which by construction carries no newline. It is a tautology,
not a regression, and the other three assertions in that test do real work
(they killed probe P4). Ranked as Observation 4.

---

## P3 Acceptance Criteria — Re-checked (evidence or zero)

| Criterion | Spec-defined outcome | `file:line` + assertion expression | Verdict |
| --- | --- | --- | --- |
| AC 1 — `phase-transitions.md` **where it describes how a halt clears** names `update_loop.py --resume`, alongside resolving the cause or changing the config | the command in the halt-clearing passage, i.e. the `H` transition row | `scripts/test_unit_docs_parity.py:384-388` `row = table_row(read_shipped("references/phase-transitions.md"), "\| \`H\` \|", …)` + `:389` `assertIn("--resume", row)`. Artifact: `references/phase-transitions.md:252` — the row reads "…a human resolves the cause, or changes the config that tripped a limit, and then runs `update_loop.py --resume`". Mutant M14 (row loses the command, file keeps it elsewhere) **killed** | ✅ PASS (precision noted — Obs. 2, 3) |
| AC 2 — `state-schema.md` **where it documents the `halt` field** names `--resume` as the writer that clears it | the command inside the `` ## `halt` `` section | `scripts/test_unit_docs_parity.py:397-399` `body = section(read_shipped("references/state-schema.md"), "## \`halt\`", …)` + `:400-404` `assertIn("update_loop.py <feature> --root <root> --resume", collapsed(body))`. Artifact: `references/state-schema.md:273-278` ("It is cleared by one command and no other:" + the fenced call). Scope proven bounded at `:425` `assertNotIn("## \`iterations[]\`", schema)`. Mutant M12 **killed** | ✅ PASS |
| AC 3 — SKILL.md **where it describes Phase H** names `--resume` as how a human lifts the halt | the command inside the `#### Phase H - Halt` branch | `scripts/test_unit_docs_parity.py:407` `body = section(read_shipped("SKILL.md"), "#### Phase H - Halt", "SKILL.md")` + `:408-413` `assertIn("update_loop.py <feature> --root <root> --resume", collapsed(body))`. Artifact: `SKILL.md:389-393` ("A human resolves the cause, or changes the config that tripped a limit, and then lifts the halt:" + the fenced call). Scope proven bounded at `:420` `assertNotIn("### Step 3", skill)`. Mutants M11b and M11c both **killed** | ✅ PASS |
| AC 4 — any shipped doc reasserting the hand-edit fails parity naming file and line | offender list `"{file}:{line} ({claim!r}): {line}"`, empty on the shipped tree | `scripts/test_unit_docs_parity.py:359-365` `assertEqual(offenders, [], …)` over `HAND_CLEARED_HALT` (`:342-347`); discrimination proof `:374-375` `assertTrue(offenders)` + `assertIn("fake.md:1", offenders[0])` | ✅ PASS (unchanged from round 1) |

**P3 status**: 4/4 at spec scope. The round-1 gap ("documented here" was
indistinguishable from "documented somewhere") is closed and empirically proven
closed by four independent placement mutants.

---

## P1 and P2 Spot-Check (round-1 coverage still holds)

`a8e92c6` did not touch `scripts/test_unit_update_loop.py` or
`scripts/test_int_end_to_end.py`, so every round-1 P1 citation is stable. All 18
cited lines were re-read and still carry the asserted expression:

| AC | `file:line` + assertion | Verdict |
| --- | --- | --- |
| P1 AC 1 | `scripts/test_unit_update_loop.py:555` `assertEqual(_run(root, "--resume").returncode, 0)` + `:556` `assertEqual(_read(root)["halt"], {"reason": None, "detail": None})` | ✅ |
| P1 AC 2 | `scripts/test_unit_update_loop.py:562` `assertEqual(_read(root)["status"], "active")` | ✅ |
| P1 AC 3 | `scripts/test_unit_update_loop.py:640` `assertEqual(_read(root)["counters"], counters)`; `:646` `assertEqual(_read(root)["iteration"], 9)`; `:658` `assertEqual(after["objective"], OBJECTIVE)` | ✅ |
| P1 AC 4 | `scripts/test_unit_update_loop.py:607` `assertEqual(len(_read(root)["iterations"]), 1)`; `:613` `assertEqual(…["phase"], "H")`; `:619` `assertTrue(…["action"].startswith("resume"))`; `:632` `assertEqual(…["action"], "resume")` | ✅ |
| P1 AC 5 | `scripts/test_unit_update_loop.py:704` `assertEqual(proc.returncode, 2)` | ✅ |
| P1 AC 6 | `scripts/test_unit_update_loop.py:713` `assertEqual(proc.returncode, 2)` | ✅ |
| P1 AC 7 | `scripts/test_unit_update_loop.py:722` `assertEqual(proc.returncode, 2)` | ✅ |
| P1 AC 8 | `scripts/test_unit_update_loop.py:585` `assertEqual(proc.returncode, 0)` | ✅ |
| P1 AC 9 | `scripts/test_int_end_to_end.py:509` `assertTrue(line.startswith("phase=H action=halt reason=gate_stuck "), line)`; `:522` same for `reason=no_progress` | ✅ |
| P1 AC 10 | `scripts/test_int_end_to_end.py:469` `before = self.detect()` + `:476` `assertEqual(self.detect(), before)` | ✅ |
| Edge 2/3/4/5 | `scripts/test_unit_update_loop.py:681`, `:740`, `:672`, `:688` | ✅ |
| P2 AC 1 | `scripts/test_unit_docs_parity.py:492-498` `body = section(…, "#### Phase B - Execute one batch", …)` + `assertIn("update_loop.py <feature> --root <root> --gate-attempt", collapsed(body))`. Artifact `SKILL.md:251`. Mutant M8 **killed** | ✅ (tightened by the fix) |
| P2 AC 2 | `scripts/test_unit_docs_parity.py:505-515` `head, _, body = text.partition("## Repair loop")` + `assertIn("--gate-attempt", section)` for both halves. Artifact `references/recovery-loop.md:18,34` | ✅ |
| P2 AC 3 | `scripts/test_unit_docs_parity.py:484-489` `assertIn("--gate-attempt", read_shipped("SKILL.md"), "SKILL.md no longer names --gate-attempt…")` | ✅ |
| P2 AC 4 | `scripts/test_unit_docs_parity.py:510-515` message `f"references/recovery-loop.md: {where} still forbids…"` | ✅ |

**Spec-anchored outcome check**: **14/14** ACs match the spec-defined outcome at
spec scope (round 1: 11/14).

---

## Discrimination Sensor — Round 2

**Isolation**: `git worktree add --detach` to a scratch path outside the repo.
File bytes were snapshotted in memory and restored after each mutation; no `git
stash`, no git writes in the worktree, and the real working tree was never
touched. Every mutation asserts its own needle applied, so a no-op edit cannot
masquerade as a verdict (`broken=0` below confirms all 20 applied).

Doc and probe mutations were judged by `test_unit_docs_parity` (35 tests);
behaviour mutations by `test_unit_update_loop`. Both modules were green on the
unmutated worktree before injection.

### Re-injected round-1 survivors — all now dead

| ID | Mutation | Verdict | Killed by |
| --- | --- | --- | --- |
| M14 | strip `update_loop.py --resume` from the `H` transition row, leave `--resume` named elsewhere in the file | ✅ KILLED | `test_the_transition_row_names_the_flag` |
| M12 | move the `--resume` block out of the `` ## `halt` `` section to the file tail | ✅ KILLED | `test_the_halt_field_section_names_the_command` |
| M11b | move the bash block out of `#### Phase H - Halt` to the file tail, leaving the prose `--resume` mentions behind | ✅ KILLED | `test_the_halt_phase_names_the_command` |
| M11c | move that block into `### Step 3`, i.e. after Phase H | ✅ KILLED | `test_the_halt_phase_names_the_command` |
| M8 | move the `--gate-attempt` call out of Phase B into Phase V | ✅ KILLED | `test_the_call_sits_in_the_phase_that_runs_the_gate` |

M11b is the decisive one: it leaves `--resume` in SKILL.md prose, so the round-1
whole-file assertion passed on it. The scoped guard fails on it.

### Probes aimed at the fix itself

| ID | Probe | Verdict | Note |
| --- | --- | --- | --- |
| P4 | `section()` first-match: strip the real Phase H block, plant a decoy `#### Phase H - Halt` heading earlier carrying the command | ✅ KILLED | `test_each_scope_excludes_the_passage_that_follows_it` — the decoy scope lacks `blast_radius`. The meta-test earns its place |
| P7 | `section()` robustness: a column-0 `#` comment inside a fence in Phase H, before the command | ⚠️ KILLED (false alarm) | `section()` treats `\n# ` inside a code fence as a heading and truncates. Kills a *harmless* edit — brittleness, not discrimination. Obs. 1 |
| P1 | `collapsed()`: the Phase H command left in place but prefixed "Never run this, it is not a supported operation" | ❌ SURVIVED | Obs. 1 |
| P1b | `collapsed()`: the real instruction replaced by "A human deletes `loop.json` and starts over. Whatever you do, never run:" + the same block | ❌ SURVIVED | Obs. 1 — intent inverted, guard green |
| P2 | `collapsed()`: the `` ## `halt` `` block wrapped in an HTML comment `<!-- … -->` | ❌ SURVIVED | Obs. 1 — commented-out code counts as documentation |
| P3 | `table_row()` first-match: strip the command from the real `H` row, plant an earlier decoy table whose `` \| `H` \| `` row carries it | ❌ SURVIVED | Obs. 2 — `table_row()` returns the *first* match |
| P5 | the `H` row names the bare `--resume` but drops `update_loop.py` | ❌ SURVIVED | Obs. 3 — AC 1 names `update_loop.py --resume` |
| P6 | the `H` row keeps the command but drops "resolving the cause / changing the config" | ❌ SURVIVED | Obs. 3 — AC 1's "alongside" clause is unasserted |

### Behaviour layer re-run (confirming the fix weakened nothing)

| ID | Mutation on `scripts/update_loop.py` | Verdict | Killed by |
| --- | --- | --- | --- |
| B1 | `_not_resumable` drops the `complete` check | ✅ KILLED | `test_a_complete_run_is_refused_naming_the_status` |
| B2 | `_not_resumable` drops the `halt.reason` check | ✅ KILLED | 3 tests incl. `test_no_recorded_halt_is_refused_naming_the_absence` |
| B3 | resume no longer sets `status = "active"` | ✅ KILLED | `test_the_run_returns_to_active`, `test_a_blocked_run_carrying_a_halt_is_resumable` |
| B4 | resume resets `counters["gate_attempts"]` | ✅ KILLED | `test_the_counters_the_halt_conditions_read_are_untouched` |
| B5 | resume appends no log entry | ✅ KILLED | 7 tests incl. `test_exactly_one_entry_is_appended` |
| B6 | the `--resume`/`--halt` contradiction check is removed | ✅ KILLED | `test_resume_together_with_halt_is_refused_as_contradictory` |
| B7 | the `LOG_LIMIT` trim is removed from `_log` | ✅ KILLED | 3 tests incl. `test_the_log_is_capped_at_the_last_fifty_entries` |

**Sensor depth**: P0-full (20 mutations; ≥5 required)
**Sensor tally**: **14 killed, 6 survived, 0 failed to apply, 20 total**

Broken out by intent: **12/12 killed** on the mutations that model real
regressions (5 placement + 7 behaviour) — the number that decides the verdict.
The 6 survivors are all adversarial probes of the guard helpers' precision, not
regressions the feature could plausibly suffer; each is ranked below.

### Isolation confirmation

| Checkpoint | `git status --porcelain` | HEAD |
| --- | --- | --- |
| Pre-sensor baseline | empty (clean) | `a8e92c6` |
| Post-sensor, worktree removed | empty (clean) | `a8e92c6` |

`git worktree list` shows only `~/Projects/tlc-loop` after `git worktree remove
--force` + `git worktree prune`. The only file this round modified in the real
tree is this report.

---

## Gate Check — Round 2

- **Gate command**: `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Exit code**: `0`
- **Outcome**: `Ran 578 tests in 155.927s` — **OK**. 578 passed, 0 failed, 0 skipped.
- **Round-1 count**: 575 → **578** (+3: the P3 guard split, 1 test out and 4 in)
- Still meets both tasks.md floors: T3 `≥ 560 total` ✅, T8 `≥ 561 total` ✅

---

## Ranked Observations (non-blocking)

None of these is a defect in the shipped artifact — `references/phase-transitions.md:252`,
`references/state-schema.md:273-278` and `SKILL.md:389-393` all satisfy their
criteria in full today. Each is a place where the *guard* binds less than the
criterion words, so a future edit could drift without tripping it.

1. **(Low) Substring guards cannot read intent — P1, P1b, P2 survived.**
   `collapsed()` (`scripts/test_unit_docs_parity.py:456-463`) normalises
   whitespace and nothing else, so the command satisfies the assertion when it
   sits inside a negation ("never run this") or an HTML comment. P1b inverts the
   Phase H instruction outright and the suite stays green. Inherent to substring
   docs-parity; a fix means asserting the command appears in a fenced block that
   no negation introduces, which is likely more machinery than the risk earns.
   Related brittleness from the same helper: P7 shows `section()` mistakes a
   column-0 `#` comment inside a fence for a heading and truncates the scope,
   so a harmless edit can fail the guard. A fence-aware scan would fix both
   directions at once.
2. **(Low-Medium) `table_row()` returns the first match — P3 survived.**
   `scripts/test_unit_docs_parity.py:466-471` iterates `splitlines()` and returns
   on the first row starting with the prefix. `references/phase-transitions.md`
   holds exactly one `` \| `H` \| `` row today, so this is latent rather than
   live; but a second phase table added above `## Derivation order` would
   silently take over the assertion. Cheap fix: collect all matching rows and
   assert on each, or raise when more than one matches.
3. **(Low) The `H`-row guard is looser than its two siblings — P5, P6 survived.**
   AC 1 asks for `update_loop.py --resume` "alongside resolving the cause or
   changing the config". `scripts/test_unit_docs_parity.py:389` asserts only
   `--resume`. The fix commit raised the other two guards and the P2 guard to
   the whole command form but left this one at the bare flag, so a row saying
   just `--resume` (P5), or one that drops the cause/config clause (P6), still
   passes. One-line fix: `assertIn("update_loop.py --resume", row)`, plus a
   second `assertIn` for the cause/config clause.
4. **(Low) One vacuous assertion.** `scripts/test_unit_docs_parity.py:431`
   `assertNotIn("\n", row)` is a tautology over a `splitlines()` element. Harmless,
   but it reads as coverage it does not provide. Replace it with a check that
   actually binds the row — e.g. that the scope excludes the neighbouring `` \| `E` \| ``
   row — or delete it.

Carried forward from round 1, still true and still not a gap: `--resume` +
`--status complete` is unspecified — `main()` runs `_not_completable`
(`scripts/update_loop.py:309-313`) before `_not_resumable` (`:315-319`).
Behaviour is sensible; no AC covers it.

---

## Requirement Traceability Update

| Requirement | Round-1 Status | Round-2 Status |
| --- | --- | --- |
| RESUME-01 (P1 AC 1, 2, 8) | ✅ Verified | ✅ Verified |
| RESUME-02 (P1 AC 3, 4) | ✅ Verified | ✅ Verified |
| RESUME-03 (P1 AC 5, 6, 7) | ✅ Verified | ✅ Verified |
| RESUME-04 (P1 AC 9, 10) | ✅ Verified | ✅ Verified |
| RESUME-05 (P2 AC 1-4) | ✅ Verified | ✅ Verified (guard tightened to the whole command) |
| RESUME-06 (P3 AC 1-4) | ❌ Needs Fix | ✅ Verified — all four ACs bound at spec scope; M11b, M11c, M12, M14 all die |

---

## Round-2 Summary

**Overall**: ✅ Ship. The round-1 defect is fixed at its root, the fix is
test-only, and it is strictly strengthening.

**Spec-anchored check**: 14/14 ACs match the spec-defined outcome at spec scope (round 1: 11/14)
**Sensor**: 20 mutations injected, **14 killed, 6 survived** — 12/12 on realistic regressions; all 6 survivors are guard-precision probes, ranked above
**Gate**: 578 passed, 0 failed, 0 skipped, exit 0
**Isolation**: pre- and post-sensor `git status --porcelain` both empty; HEAD unchanged at `a8e92c6`
**Weakening audit**: no test deleted, skipped, or loosened; 1 vacuous assertion found (Obs. 4)

**What the fix got right**: it repaired the root cause rather than the three
symptoms, and the `section()` level fix caught a second bug the round-1 report
did not name — `#### Phase H` being the last `####` in the file meant the
"scoped" scan would have run to EOF and reproduced the original whole-file
weakness under a new name. The added meta-test
(`scripts/test_unit_docs_parity.py:415`) is what proves the scopes are real, and
it killed probe P4 unaided.

**Remaining work**: none blocking. Observations 1-4 are optional hardening of
the docs-parity helpers and can be picked up whenever that file is next touched.

---

## Round 1 (superseded): halt-resume - FAIL ❌

*Kept for history. Superseded by the round-2 report above; the three gaps it
raises were fixed in `a8e92c6` and re-tested. Heading relabelled from
`## Validation:` so the completion gate reads only the round-2 verdict.*

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
**Sensor outcome**: 13/16 killed, 3 survived - FAIL ❌

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
