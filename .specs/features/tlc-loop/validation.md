# Validation: tlc-loop — Round 7 (publication gate) — PASS

**Date**: 2026-08-09
**Spec**: `.specs/features/tlc-loop/spec.md`
**Diff range**: `12bd8c3..e3038d2` (full surface); `17fe800..e3038d2` new since round 6 (T44, T45, T46 + one follow-up)
**Verifier**: independent sub-agent, round 7 (author ≠ verifier; did not write rounds 1–6 or their reports)
**Verdict**: ✅ **PASS — publish**

---

## Verdict in one paragraph

Round 6's three findings are closed, and I re-derived each from the artifacts rather than
from its report. **T44 is real, not nominal.** All three approval-bypass arguments exist in
their own CLI's `--help` on this machine, and all three argv shapes were additionally accepted
by the real parsers (`codex exec` failed only on a deliberately nonexistent `-C`; `claude`
failed only on a deliberately bogus `--output-format`). Every `command` path carries its bypass
under *environment-detected* harnesses, not only under `--harness` — I ran the resolver with
`CURSOR_AGENT=1`, with `CLAUDECODE=1`, and with no marker at all, and the claude, codex, and
cursor command lines each carried theirs in every case where they were not the native agent.
`{perm}` is gone. **T45 is real**: the no-diff contract has exactly one full description
(`references/state-schema.md:139-167`), the twelve other mentions across the shipped surface are
pointers, the self-contradiction is gone, and the corrected sentence at `references/state-schema.md:243-245`
matches `scripts/update_loop.py:163-164`. **T46 is real**: two full-suite runs left zero probe
processes, swept with `pgrep` myself. The gate is **396 passed, 0 failed, 0 skipped**, twice,
with **+4 tests and none removed or weakened**. Fifteen mutations: **12 killed, 3 survived** —
one provably equivalent, one documentation-only, one test scaffolding.

I looked hard for a seventh overnight-killer. I did not find one. What I found is three minor
items, recorded below as follow-ups rather than blockers: an unhandled `PermissionError` class in
`_spawn.py`'s kill escalation that I observed crash the spawner exactly once in 33 runs and could
not reproduce in 1000+ further attempts; an approval hazard documented for the `command` path and
unmentioned for the `agent` path that the default configuration actually uses; and a surviving
documentation mutant showing that T45's structural fix is not backed by any check that the
structure holds. None is a false claim shipping today, none corrupts state, none hangs an
unattended run, and the two genuine overnight-killers found in rounds 5 and 6 are both dead and
independently re-verified.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1–T43 | ✅ Done | Verified rounds 1–6; re-confirmed green here |
| T44 — every command executor runs without prompting | ✅ Done | All six Done-when independently reproduced (§3) |
| T45 — one canonical description of the no-diff contract | ✅ Done | 10 → 1 verified by grep, not by the commit message (§4) |
| T46 — cleanup that survives a SIGTERM-immune probe | ✅ Done | Zero survivors after two full-suite runs (§5) |

---

## 1. Gate Check

- **Gate command** (Build, `tasks.md:36`):
  `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Result at HEAD `e3038d2`, real tree**: **396 passed, 0 failed, 0 skipped**, 72.0s
- **Result in the sensor worktree (same HEAD)**: **396 passed, 0 failed, 0 skipped**, 73.4s
- **Test count**: 392 (round 6) → **396** (+4)
- **Skipped**: none

### Test integrity across `17fe800..HEAD`

I diffed every `def test_` name at both revisions, per file:

| | |
| --- | --- |
| Added | 4, all in `scripts/test_unit_resolve_stage.py` (37 → 41) |
| Removed | **0** |
| Renamed | **0** |
| Per-file counts | identical for all 15 other test files |

**The one restructured test** is `test_the_model_and_effort_use_the_verified_codex_flags`
(`scripts/test_unit_resolve_stage.py:72-81`). T44 inserted the bypass between `exec` and `-m`,
so the old single substring `assertIn("codex exec -m gpt-5.6-luna", line)` could no longer hold.
It became two assertions:

```python
self.assertIn("cmd=codex exec ", line)
self.assertIn("-m gpt-5.6-luna", line)
```

**Specificity is not reduced.** The old form asserted adjacency of `exec` and `-m` — a property
that is no longer true — and said nothing about where `codex` sat on the line. The new form pins
`codex exec` to *immediately follow* `cmd=`, which the old form did not, and pins the model flag
and its value separately. It is strictly stronger on position and weaker only on an adjacency that
the change deliberately removed. `test_it_resolves_to_a_command` (`:66-70`) independently asserts
`line.startswith("kind=command provider=codex cmd=")`.

---

## 2. Spec-Anchored Acceptance Criteria

Evidence-or-zero. Every `file:line` below was opened and read this round; nothing is inherited
from round 6's table.

### LOOP-01 — Deterministic phase detection and resume (P1)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — exactly one phase line before any work | one line, printed first | `scripts/test_unit_detect_phase.py:212` — `assertEqual(len(lines), 1, f"expected exactly one line, got {lines!r}")`, inside `line()`, which every detect test in the file routes through | ✅ |
| AC2 — completed tasks from `git log --format="%(trailers:key=Task,valueonly)"`, authoritative over `loop.json` | git wins | `scripts/_gitio.py:21` uses that exact format; `scripts/test_unit_gitio.py:179-191` — `assertEqual(git log -1 --format=%(trailers:key=Task,valueonly), "T3")`; `scripts/test_unit_detect_phase.py:302-310` `test_git_wins_over_conflicting_state` — `assertEqual(line, "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6")` while state still claims T1 in flight | ✅ |
| AC3 — absent `loop.json` reconstructs, does not fail | `phase=0 action=bootstrap`, then the same next task | `scripts/test_unit_detect_phase.py:228-230` — `assertNotIn("phase=H", self.line())`; `:232-247` `test_deleting_the_state_file_costs_no_task_progress`; `:248-264` for the no-diff case | ✅ |
| AC4 — unparseable `loop.json` halts `state_corrupt` | `phase=H action=halt reason=state_corrupt` | `scripts/test_unit_detect_phase.py:710-714` — `assertTrue(self.line().startswith("phase=H action=halt reason=state_corrupt "))`; `:736-741` `test_corrupt_state_is_never_reconstructed_into_work` | ✅ |
| AC5 — disagreement: git wins and the reconciliation is recorded | task stays pending, `reconciled=` on the line, durable via `update_loop.py` | `scripts/test_unit_detect_phase.py:332-339` — `assertEqual(line, "... tasks=T1,T2,T3,T4,T5,T6 reconciled=T1")`; `:346-351` still dispatched; `scripts/test_unit_update_loop.py:278-286` — `assertEqual(entries[0]["task"], "T4")`, `assertEqual(entries[0]["winner"], "git")` | ✅ |
| AC6 — `loop.json` mutated only through its own writer | single writer | `scripts/test_unit_update_loop.py:150-181` — `--objective` rejected and no other flag applied; `scripts/test_unit_detect_phase.py:675-689` — state bytes, porcelain and HEAD all byte-identical after a detect | ✅ |

### LOOP-02 — Atomic checkpoint per task (P1)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — one atomic commit with `Task:` and `Gate: <level> PASS` | both trailers present | `scripts/test_unit_checkpoint.py:203-206` — `assertEqual(self.trailer("Task"), "T7")`; `:208-211` — `assertEqual(self.trailer("Gate"), "build PASS")` | ✅ |
| AC2 — no commit when the gate has not passed | commit count unchanged | `scripts/test_unit_checkpoint.py:137-157` — omitted, failing and non-exact `--gate-result` all leave `commit_count()` unchanged | ✅ |
| AC3 — validate the message with `check_commit.py`, abort non-zero | refuse, nothing staged | `scripts/test_unit_checkpoint.py:167-178`; `scripts/test_int_tlc_validators.py:295-333` exercises the **real** sibling validator | ✅ |
| AC4 — at most one commit per task, never batched | exactly +1 | `scripts/test_unit_checkpoint.py:196-201` — `assertEqual(self.commit_count(), before + 1)` | ✅ |
| AC5 — an executor may not commit; the loop creates the checkpoint | prohibition + recovery | Prose only: `SKILL.md:63-65`, `references/executors.md:20-47`, `references/recovery-loop.md:87` | ⚠️ prose |
| AC6 — a no-diff task records completion without fabricating a diff | empty commit carrying the trailers | `scripts/test_unit_checkpoint.py:290-296` — `assertEqual(self.trailer("Task"), "T7")` and `assertEqual(self.trailer("Gate"), "quick PASS")`; `:298-303` `test_that_commit_fabricates_no_source_diff` — `assertEqual(changed, [])`; `:315-325` reads it back through `_gitio.completed_tasks` | ✅ |

### LOOP-03 — Self-healing repair loop (P1) — prose

No AC in this story has an executable form: they govern agent behaviour, not a script. All five
verified by review against `references/recovery-loop.md`, which I re-read in full this round and
found coherent and current (`:86` correctly describes the post-T37 empty commit and now links to
the canonical section).

| Criterion | Evidence | Result |
| --- | --- | --- |
| AC1 — a failure keeps the phase open, writes no final state | `references/recovery-loop.md:12-15,24-26`; `SKILL.md:95-98` | ⚠️ prose |
| AC2 — diagnose before retrying; never a bare rerun | `references/recovery-loop.md:27-37` | ⚠️ prose |
| AC3 — never weaken/delete/skip a test | `references/recovery-loop.md:49-66`; `SKILL.md:67-69` | ⚠️ prose |
| AC4 — repair and continue rather than report a blocker | `references/recovery-loop.md:76-97`, `:140-155` | ⚠️ prose |
| AC5 — all three blocker criteria, evidence, halt, no signature | `references/recovery-loop.md:126-142,157-173` | ⚠️ prose |

### LOOP-04 — Independent verification with bounded fix loop (P1)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — dispatch a fresh verifier, unprompted | never asked | Prose: `SKILL.md:249-253`, `references/executors.md:161-169` | ⚠️ prose |
| AC2 — verifier read-only on the real tree | no code/test mutation | Prose: `SKILL.md:254-255`, `references/executors.md:166-168` | ⚠️ prose |
| AC3 — FAIL routes gaps to `fix`, then re-verify | `phase=F` then `phase=V` | `scripts/test_unit_detect_phase.py:499-504` — `assertEqual(self.line(), "phase=F action=fix round=1")` with `gaps_open>0`; `:492-497` — FAIL with 0 gaps returns to `phase=V` | ✅ |
| AC4 — verify-round limit reached without PASS ⇒ halt | `reason=verify_exhausted`, checked before a round is named | `scripts/test_unit_detect_phase.py:522-536`; `:537-545` `test_the_ceiling_is_checked_before_a_fix_round_is_emitted` | ✅ |
| AC5 — PASS confirmed by `validate_state.py`; non-zero is not done | exit 0 required | `scripts/test_unit_detect_phase.py:574-580` — `assertEqual(self.line(), "phase=E action=done")` only with a PASS report whose `verified_at` is HEAD; `:581-586` a FAIL report does not; `scripts/test_int_tlc_validators.py:364-392` runs the **real** validator (FAIL verdict, unfilled template, and a PASS with no `file:line` are all rejected); `:603-612` a commit after the PASS reopens verification | ✅ |

### LOOP-05 — Per-stage provider, model, and effort (P1)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — resolve provider/model/effort from config through the adapter table | translated command line, per the table in `references/providers.md` | `scripts/test_unit_resolve_stage.py:72-87` (codex: `cmd=codex exec `, `-m gpt-5.6-luna`, `-c model_reasoning_effort=max`, `-o /tmp/e.txt`), `:91-111` (cursor bracket syntax `claude-opus-5[effort=high]`, no `--effort`, `--force`, `--output-format json`), `:194-206` (claude `--model opus` + `--effort high`, `kind=command` off-harness), `:156-191` (every builtin carries its bypass). **Round 6's gap is closed** — §3 | ✅ |
| AC2 — reject an unsupported effort before dispatch | named stage, provider, accepted set | `scripts/test_unit_resolve_stage.py:252-262` — `assertIn("implement", …)`, `assertIn("claude", …)`, all accepted values listed; `:268-271` — `ultra` rejected by all three; `scripts/_config.py:88-99` rejects it at load, before dispatch. See §7 observation 2 on which layer actually fires | ✅ |
| AC3 — provider == harness ⇒ harness-native sub-agent | `kind=agent`, no `cmd=` | `scripts/test_unit_resolve_stage.py:212-217` — `assertEqual(line, "kind=agent provider=claude model=opus effort=high")`; `:219-222` — `assertNotIn("cmd=", line)`; reproduced live with `CLAUDECODE=1` (§3) | ✅ |
| AC4 — config read-only; runtime values in `loop.json` | never written | `scripts/resolve_stage.py` has no write path (verified by reading the module); `scripts/test_unit_detect_phase.py:675-689` proves the read path writes nothing; `scripts/test_unit_init_loop.py:261-268` — `assertEqual(self.state()["harness_resolved"], "claude"/"cursor")` | ✅ |
| AC5 — launch/auth/quota failure ⇒ halt with the reason recorded | `reason=executor`, resumable | `scripts/update_loop.py:44-53` (`executor` in `HALT_REASONS`); `scripts/test_int_loop_sh.py:390-404` — `assertIn("--halt executor", recorded[0])` and `assertIn("executor_timeout_seconds", recorded[0])`. The agent path is prose (`references/recovery-loop.md:92-94`); the shell driver records only the timeout case — §7 observations 4 and 5 | ⚠️ partial |
| AC6 — verify the executor's evidence before advancing | no completion without artifact | Prose: `SKILL.md:216-217`, `references/executors.md:49-71`, `references/recovery-loop.md:87` | ⚠️ prose |

### LOOP-06 — Unattended continuation and stop conditions (P1)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — re-enter detection in the same turn | never return control mid-run | Driver: `scripts/test_int_loop_sh.py:211-225` `test_spawns_for_every_non_terminal_phase`; `scripts/loop.sh:163-221`. Agent: prose `SKILL.md:344-348` ("no config key disables this") | ⚠️ partial (driver tested, agent prose) |
| AC2 — print the done-signature once `validate_state.py` exits 0 | `__TLC_LOOP__ feature=<f> verify=PASS` | Gating tested: `scripts/test_unit_detect_phase.py:574-580` / `:581-586`. String identical in all five shipped places: `SKILL.md:307`, `README.md:123`, `assets/goal-condition.template.md:11,25,67`, `assets/iteration-summary.template.md:36`, `references/checklist.md:128` (verified by grep). The printing itself is prose | ⚠️ partial |
| AC3 — resolve continuation from the harness, record it | `harness_resolved` in state | `scripts/test_unit_init_loop.py:261-268` — `assertEqual(self.state()["harness_resolved"], "claude")` and `"cursor"` | ✅ |
| AC4 — inconclusive detection halts and asks | non-zero, no state file | `scripts/test_unit_init_loop.py:273-288` — `assertNotEqual(rc, 0)`, `assertIn("--respawn", stderr)`, `assertFalse(exists(state_path))`, and two markers at once is inconclusive rather than guessed | ✅ |
| AC5 — objective immutable | verbatim, unchangeable | `scripts/test_unit_init_loop.py:244-256`; `scripts/test_unit_update_loop.py:150-181` — `--objective` rejected and the rejected call applies none of its other flags | ✅ |
| AC6 — no new commit across N iterations ⇒ halt | `reason=no_progress` | `scripts/test_unit_update_loop.py:202-217` — increments without `--commit`, `assertEqual(counters["iterations_without_commit"], 0)` with it; `scripts/test_unit_detect_phase.py:643-647` — `assertIn("reason=no_progress", self.line())` at the limit | ✅ |
| AC7 — gate failing past N attempts ⇒ halt | `reason=gate_stuck` | `scripts/test_unit_update_loop.py:184-199`; `scripts/test_unit_detect_phase.py:648-654` — `assertIn("reason=gate_stuck", line)` and the task named | ✅ |
| AC8 — `max_iterations` / `max_minutes` reached ⇒ write state, halt cleanly, resumable | `reason=limit` | `scripts/test_unit_detect_phase.py:655-659`; `:664-673` — an omitted limit never fires even at iteration 9999 | ✅ |
| AC9 — remote/destructive work halts for authorization | `reason=blast_radius`, waits | Vocabulary tested (`scripts/update_loop.py:44-53`, `scripts/test_unit_update_loop.py:383-401`); the judgement is prose (`SKILL.md:71-83`, `references/recovery-loop.md:101-126`) | ⚠️ prose |
| **executor timeout** (T39/T41, under AC1/AC8) | expiry killed, recorded `reason=executor` | `scripts/test_unit_spawn.py:140-263` (7 tests, each ending in a `pgrep` survivor assertion); `scripts/test_int_loop_sh.py:324-560,562-651`. Independently re-exercised this round: 400/400 `_spawn.py --timeout 0.2 -- 'sleep 5'` returned exactly 124 | ✅ (see Gap 1) |

### LOOP-07 — Handoff from tlc-spec-driven (P2)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — Execute offers loop mode alongside inline and sub-agents | three options | `<skills-dir>/tlc-spec-driven/references/sub-agents.md:40-47` — the offer block lists Inline, Phase-batch sub-agents, and Loop mode (`/tlc-loop [feature]`) | ⚠️ review-only, §7 obs. 6 |
| AC2 — declining falls back to unchanged behaviour | inline | same file `:48-50` — "The user must explicitly accept. If they decline … execute inline." | ⚠️ review-only |

### Coverage totals (re-derived independently)

| | P1 | P2 | Total |
| --- | --- | --- | --- |
| Acceptance criteria (6+6+5+5+6+9 P1; 2 P2) | 37 | 2 | **39** |
| Covered by an assertion targeting the spec-defined outcome | 24 | 0 | **24** |
| Prose / review-only (no executable form) | 10 | 2 | **12** |
| Partial (one path tested, the other prose) | 3 | 0 | **3** |

The three partials are LOOP-05 AC 5, LOOP-06 AC 1, and LOOP-06 AC 2.

**Reconciling `README.md:196`** ("Thirteen acceptance criteria are prose, verified by review
rather than by a test"): 10 purely-prose P1 criteria + 3 partials = **13 P1 criteria not fully
pinned by an assertion**. The number is right for P1 and excludes the 2 P2 review-only criteria,
which would make 15. Round 6 arrived at 13 by a different split of the same set. Recorded as a
precision note in §7, not a gap — the disclosure's substance is accurate under either split.

---

## 3. T44: every command executor runs without prompting

Round 6's blocker was that `references/providers.md` and `references/recovery-loop.md` promised a
safety property `scripts/resolve_stage.py` implemented for one provider of three. I re-derived
each Done-when rather than reading the task's ticks.

### The flags exist, in each CLI's own `--help`, on this machine

| Provider | Argument the loop passes | `--help` evidence |
| --- | --- | --- |
| claude | `--dangerously-skip-permissions` | `claude --help`: `--dangerously-skip-permissions   Bypass all permission checks.` |
| codex | `--dangerously-bypass-approvals-and-sandbox` | `codex exec --help`: `Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY DANGEROUS.` |
| cursor | `--force` | `cursor-agent --help`: `-f, --force   Force allow commands unless explicitly denied` |

`claude --help` also confirms `--effort <level>`, `--model <model>`, `-p/--print` and
`--output-format`; `codex exec --help` confirms `-m`, `-c`, `-C/--cd` and `-o/--output-last-message`;
`cursor-agent --help` confirms `-p`, `--model` with bracket overrides, and `--output-format`.

### The whole argv shape is accepted by the real parsers

`--help` proves a flag is listed; it does not prove the combination parses. Two zero-API-cost
probes, each bounded by the skill's own `scripts/_spawn.py`:

| Probe | Result |
| --- | --- |
| `codex exec --dangerously-bypass-approvals-and-sandbox -m … -c model_reasoning_effort=high -C /nonexistent-dir-xyz -o … 'x'` | `Error: No such file or directory (os error 2)` — every flag parsed; it failed only on the directory I made up |
| `claude -p 'x' --dangerously-skip-permissions --model opus --effort high --output-format bogusfmt` | `error: option '--output-format <format>' argument 'bogusfmt' is invalid` — every other flag parsed; it failed only on the value I made up |
| `cursor-agent -p '…' --force --output-format text` in a never-before-seen git repo, stdin closed, bounded 45s | returned **0** in ~30s having produced the requested output. No workspace-trust prompt, no approval prompt. (`cursor-agent` also has a separate `--trust` flag; it is not needed for `-p`.) |

### No provider depends on the operator's global configuration

Round 6's exact concern. I resolved all three stages under three *environment-detected* harnesses,
with no `--harness` flag, against a config naming codex / claude / cursor:

| Harness in the environment | implement (codex) | verify (claude) | fix (cursor) |
| --- | --- | --- | --- |
| `CURSOR_AGENT=1` | `cmd=codex exec --dangerously-bypass-approvals-and-sandbox …` | `cmd=claude -p go --dangerously-skip-permissions …` | `kind=agent` (native) |
| `CLAUDECODE=1` | `cmd=codex exec --dangerously-bypass-approvals-and-sandbox …` | `kind=agent` (native) | `cmd=cursor-agent -p go --force …` |
| no marker at all | `cmd=codex exec --dangerously-bypass-approvals-and-sandbox …` | `cmd=claude -p go --dangerously-skip-permissions …` | `cmd=cursor-agent -p go --force …` |

The claude *command* path — invisible under Claude Code, which resolves it to `kind=agent` — is
the one round 6 said shipped bare. It carries the flag. `~/.codex/config.toml`'s
`approval_policy` is no longer load-bearing.

### `{perm}` is gone, and the family is pinned family-wide

`git ls-files | xargs grep '{perm}'` finds it only in `.specs/` prose *about* its removal
(`design.md:381`, `tasks.md:1497`). It is absent from `references/providers.md`, whose placeholder
table (`:45-62`) lists exactly `{model}`, `{effort}`, `{repo}`, `{evidence}`, `{prompt}`.

`scripts/test_unit_resolve_stage.py:156-159` asserts `sorted(resolve_stage.BUILTIN) ==
sorted(EXPECTED)` with `EXPECTED` written out literally rather than read from the resolver — so a
fourth provider cannot be added without a deliberate decision about its bypass. Mutation M8
confirms that pin fires (§6).

### The risk is stated where a user meets it

Not only in a reference: `README.md:175-185` (the first bullet of "Known limitations", naming all
three flags, saying codex also runs unsandboxed, and telling the reader to run it on a machine
they would not mind losing), `SKILL.md:85-93` (a Critical rule), `references/executors.md:75-101`,
`references/providers.md:213-241`, `references/recovery-loop.md:117-126`.

**A custom `[providers.<name>]` gets no bypass and is not refused.** `scripts/resolve_stage.py:171-175`
substitutes the template as written; `test_a_custom_provider_is_the_operators_own_responsibility`
(`scripts/test_unit_resolve_stage.py:182-191`) pins that. **I judge this correct**: the loop has no
catalogue for an arbitrary CLI, so it cannot supply the flag, and refusing every declared provider
would remove the escape hatch the design depends on (`references/executors.md:257-277`). It is
stated three times where the reader will be (`SKILL.md:91-93`, `references/executors.md:100-101`,
`references/providers.md:202-206`), each time as an instruction to the template author rather than
a footnote. A refusal would be the wrong trade; a silent gap would not — this is neither.

---

## 4. T45: one description, and it is the right one

**The count.** I grepped the mechanism (`no.diff`, `allow-empty`, `empty commit`, `changed nothing`,
`produced no`, `commitless`, `PASS empty`, `no_diff_tasks`) across every shipped file, then read
each hit.

- **One full description**: `references/state-schema.md:139-167`, "The no-diff contract", opening
  with the rule that makes it the only one.
- **Twelve pointers**, each a link or a one-clause summary that defers: `references/state-schema.md:85-86`,
  `:101`, `:123`, `:243-245`; `references/phase-transitions.md:98`, `:139-142`, `:228`;
  `references/recovery-loop.md:86`; `SKILL.md:54-55`, `:224-226`; `scripts/checkpoint.py:18-21`
  and `:172-173`; `scripts/detect_phase.py:181-184`; `scripts/update_loop.py:120-123`.
- **Is any "pointer" a restatement in disguise?** One is close: `references/state-schema.md:243-245`
  states the counter consequence in place before linking. I judge it a scoped statement rather than
  a second explanation — it is the correction round 6 demanded, it carries one of the three
  consequences and not the mechanism, and it links. `references/checklist.md:66-67` mentions
  `PASS empty` as an observable to check, not as an explanation. Everything else is a bare link.
- `references/state-schema.md` no longer contradicts itself: the only two statements about the
  counter (`:159-161` and `:243-245`) agree.

**The corrected sentence, checked against the code rather than against the commit message.**
`references/state-schema.md:243-245` now reads *"A task that changed nothing is not a commitless
iteration: it is committed empty, so it resets this counter like any other task."* Traced:

1. `scripts/checkpoint.py:174-175` — `empty = git diff --cached --quiet == 0`, `allow_empty = ["--allow-empty"] if empty else []`.
2. `scripts/checkpoint.py:178-185` — the commit is made and a real short SHA is printed, the line ending `PASS empty`.
3. `SKILL.md:235-242` — the loop closes the iteration with `--commit <sha>`.
4. `scripts/update_loop.py:163-164` — `if args.commit: state["counters"]["iterations_without_commit"] = 0`.

So yes: it resets, exactly as claimed. Pinned by `scripts/test_unit_update_loop.py:210-217` and by
mutation M13 (§6). Round 6's Gap 2 is closed.

**The count is in the commit message**, as T45's fourth Done-when requires: `cc09a19` states
"Independent explanations of the no-diff contract: 10 -> 1" and enumerates the nine sites it
converted. (It lists `SKILL.md` once where there are two mentions; both are pointers, so the
substance holds.)

**The `.specs/` planning record still explains the mechanism independently** (`design.md:215,302,417,429`)
— all four statements are *correct*, and a design record is a historical artifact rather than
instruction. Out of scope for the one-description rule, noted so a future round does not re-litigate it.

---

## 5. T46: the suite leaves nothing behind

`scripts/test_unit_spawn.py:73-91` replaced the bare `pkill` with `reap()`, which escalates
`SIGTERM` → `SIGKILL` and returns survivors; `:114-120` `assert_reaped` then asserts the tree is
empty, registered by `token()` (`:104-112`) for every test.

**Swept myself, twice.** After the full 396-test suite on the real tree and again after the same
suite in the scratch worktree:

```
pgrep -fl "tlcspawn|sleep 600|_spawn.py|probe.py"   →   (nothing)
```

Three zero-byte `$TMPDIR/tlc-loop-evidence-*` files exist, timestamped 04:00–04:10 — round 6's
own `SIGKILL` probe, which no trap can catch, and which round 6 recorded. My runs created none.

Round 6's Gap 3 is closed. The comment now matches the behaviour (`:107-110`).

---

## 6. Discrimination Sensor

**Scratch**: `git worktree add --detach <scratchpad>/sensor/tlc-loop HEAD`, with `tlc-spec-driven`
symlinked beside it so `_paths.tlc_dir()` resolves (verified before starting). Baseline in the
scratch: **396 green**. No `git stash`. The real worktree was never written.

**Isolation verified.** `git status --porcelain` captured before the sensor and again after
`git worktree remove --force` is byte-identical (` M .specs/LESSONS.md`,
` M .specs/features/tlc-loop/validation.md`, ` M .specs/lessons.json` — the pre-existing
lessons/report edits, nothing else). `git rev-parse HEAD` unchanged (`e3038d2`). The scratch was
clean at removal.

**Depth**: expanded (15 mutations), weighted to `resolve_stage.NON_INTERACTIVE` and the command
builders (10 of 15) per the brief, with the no-diff contract, the counter, and the T46 cleanup
covering the rest.

| # | File:line | Mutation | Killed? | Killing assertion |
| --- | --- | --- | --- | --- |
| M1 | `scripts/resolve_stage.py:83` | claude flag → `--dangerously-skip-permission` (one-character typo) | ✅ Killed | `test_unit_resolve_stage.py:161` `test_every_builtin_command_provider_passes_its_argument` (provider='claude'), and `:172` |
| M2 | `scripts/resolve_stage.py:84` | codex flag → `--approve-for-me` (a real but wrong codex flag) | ✅ Killed | same two, provider='codex' |
| M3 | `scripts/resolve_stage.py:85` | cursor flag → `--auto-review` (a real but wrong cursor flag) | ✅ Killed | `:107` `test_the_non_interactive_flags_are_present`, plus both dispatch tests |
| M4 | `scripts/resolve_stage.py:94` | drop the bypass from `_claude_argv` entirely | ✅ Killed | `:161`, `:172` (provider='claude') |
| M5 | `scripts/resolve_stage.py:103` | drop the bypass from `_codex_argv` entirely | ✅ Killed | `:161`, `:172` (provider='codex') |
| M6 | `scripts/resolve_stage.py:112` | drop the bypass from `_cursor_argv` entirely | ✅ Killed | `:107`, `:161`, `:172` |
| M7 | `scripts/resolve_stage.py:103-105` | the codex bypass rides `if model:` — present only when a model is configured | ✅ Killed | `:172` `test_the_argument_does_not_depend_on_a_model_or_an_effort` — the test written for exactly this |
| M8 | `scripts/resolve_stage.py:120-124` | add a fourth `BUILTIN` provider with no `NON_INTERACTIVE` entry | ✅ Killed | `:156` `test_every_builtin_command_provider_pins_its_argument_here` |
| M9 | `scripts/resolve_stage.py:158` | remove the `check_effort(provider, effort, name)` call from `resolve()` | ❌ **Survived — proven equivalent** | see below |
| M10 | `scripts/resolve_stage.py:162` | `provider == harness` no longer returns `kind=agent` (LOOP-05 AC 3) | ✅ Killed | `:212`, `:219`, `:398` |
| M11 | `references/state-schema.md:243-245` | revert to round 6's **exact** false wording ("records no commit, so it increments this counter") | ❌ **Survived** | nothing — see Gap 3 |
| M12 | `references/state-schema.md:243-245` | the same falsehood, worded with one of the scanner's own needles ("produced no commit") | ✅ Killed | `test_unit_docs_parity.py:290` `test_no_shipped_document_describes_the_retired_mechanism` |
| M13 | `scripts/update_loop.py:163-164` | a recorded commit no longer resets `iterations_without_commit` | ✅ Killed | `test_unit_update_loop.py:210` `test_it_resets_to_zero_when_a_commit_is_recorded` |
| M14 | `scripts/checkpoint.py:175` | drop `--allow-empty`, so a no-diff task gets no commit | ✅ Killed | `test_unit_checkpoint.py:285`, `:315`, `:282` |
| M15 | `scripts/test_unit_spawn.py:84` | remove the `SIGKILL` escalation from `reap()` | ❌ **Survived** | scaffolding — see below |

**Sensor result**: **12 / 15 killed**. All ten mutations aimed at `NON_INTERACTIVE` and the
command builders were killed, including the two subtlest (M7's conditional bypass and M8's
unpinned fourth provider).

**M9 is an equivalent mutant, and I can prove it.** `check_effort` (`scripts/resolve_stage.py:127-136`)
narrows per provider, but `PROVIDER_EFFORTS[p] ⊇ _config.EFFORTS` for all three providers
(`claude` and `cursor` equal it; `codex` adds `minimal`), and `_config._check_effort`
(`scripts/_config.py:88-99`) already rejects anything outside `EFFORTS` at load time. There is
therefore no config value that reaches `resolve()` and that `check_effort` would reject: the call
cannot change any observable output, so no test can kill it. Not a discrimination gap. It is
defence-in-depth that becomes live only if a future provider's accepted set is narrower than the
union — recorded as observation 2.

**M15 is test scaffolding whose activation condition is a broken spawner.** On a green suite
`_spawn.py` has already killed every probe, so `reap()` finds nothing and the escalation is never
exercised. I verified the guarantee directly instead of by mutation: after both full-suite runs a
`pgrep` sweep found zero probes (§5), and `reap()`'s escalation is the documented answer to the
eleven probes round 6 had to clear by hand. Not counted as a discrimination gap in product code.

**M11 is a genuine survivor** and is recorded as Gap 3.

---

## 7. Gaps and observations

### Gap 1 (Minor) — `_spawn._signal_group` handles one errno, and I watched the other one crash it

`scripts/_spawn.py:57-62`:

```python
def _signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass
```

`os.killpg` can also raise `PermissionError`. `terminate()` (`:70-81`) calls
`proc.wait(timeout=grace)` — which **reaps** the child and releases its pid when the group has
emptied — and then signals `proc.pid` unconditionally. Signalling a pid after `wait()` has
returned is a use-after-free of the pid namespace: the only case in which the escalation can
target the wrong group is the case in which it has nothing left to do.

**Observed, not theorised.** One run of `scripts/test_unit_spawn.py` at HEAD, in the clean scratch
worktree, ended `FAILED (failures=1)` with the spawner's own stderr showing
`PermissionError: [Errno 1] Operation not permitted` raised from `_spawn.py:80` via `:60` — i.e.
`_spawn.py` exited with a traceback instead of returning `TIMED_OUT`.

**How rare.** Not reproduced in: 33 further runs of that file (10 of them under deliberate pid
churn), 400 direct `_spawn.py --timeout 0.2 -- 'sleep 5'` invocations (histogram: `{124: 400}`),
or 600 iterations of a signal-0 probe replaying `terminate()`'s exact sequence.

**Consequence if it fires in a run.** `_spawn.py` exits non-zero with a status that is neither 0
nor 124, so `scripts/loop.sh:219-220` takes `die 2 "respawn command exited N"` — the run stops
**without** `update_loop.py --halt executor` being recorded. LOOP-05 AC 5's "halt with that reason
recorded" is not met on that path. State is intact, nothing is corrupted, and re-invoking resumes.

**Why this is not a blocker.** It needs `limits.executor_timeout_seconds`, which is unset by
default (`references/config-schema.md:181`); it stops rather than hangs; it leaves the run
resumable; and I could not make it happen again in over a thousand attempts. It is worth fixing —
catch `OSError` in `_signal_group`, and skip the escalation when `proc.wait(timeout=grace)`
returned rather than timed out — but it does not stand between this repository and publication.

### Gap 2 (Minor) — the approval hazard is documented for the path the default config does not use

Five shipped documents explain, at length, that a **`command`** executor runs with its approval
guardrail off. Nothing anywhere says what the **`agent`** path does. That path is not an edge
case: with no `.specs/loop.config.toml` every stage defaults to `provider = "auto"`
(`scripts/_config.py:40,63-77`), `auto` resolves to the running harness
(`scripts/resolve_stage.py:139-144`), and a matching provider returns `kind=agent` (`:162-164`).
Under Claude Code — the harness the README leads with — the default configuration therefore
dispatches **every** stage as a harness-native sub-agent, whose tool calls inherit the session's
own permission mode. If that session prompts, the turn never ends, `/goal` never re-fires, and the
run is asleep until morning: precisely the failure `README.md:175-185` exists to warn about, on the
one path it does not mention.

The loop cannot fix this in code — LOOP-05 AC 3 mandates the native path, and a skill cannot change
its host's permission mode mid-session. It can say so. `README.md`'s "Known limitations" is the
right place, and one sentence ("start the session in a mode that will not prompt") would close it.

**Why this is not a blocker.** Nothing claims the native path is prompt-free; the section is
scoped, in its own heading, to `command` executors (`references/executors.md:75`). This is an
omission, not a false statement, and the hazard belongs to the operator's harness rather than to
the loop.

### Gap 3 (Minor) — T45's structure is not backed by any check that the structure holds

Mutation M11 restored `references/state-schema.md:243-245` to the exact sentence that shipped false
in round 6 and the suite stayed green. M12 shows the backstop still fires for its own four needles
(`scripts/test_unit_docs_parity.py:223-233`), so the scanner works — it simply cannot see this
wording, which is why round 6 found it by reading.

Two things follow, and I record both because they pull in opposite directions:

1. T45's own docstring (`scripts/test_unit_docs_parity.py:281-288`) says *"Extend it only to nail a
   specific phrasing that has already shipped."* "records no commit" is a phrasing that has already
   shipped, and it was not added. T45 did not apply its own rule to the sentence it was fixing.
2. The rule T45 replaced the scanner with — one full description, everything else a link — is
   asserted by nothing. No test counts the explainers, and no test checks that a mention outside
   `state-schema.md` contains a link. The structural fix is real (§4 verifies it holds today) but it
   is preserved by discipline alone, which is what the previous three attempts also relied on.

**Why this is not a blocker.** The shipped sentence is correct today, verified against the code
(§4), and the file no longer contradicts itself. This is about the durability of the fix, not its
truth.

### Observations (not gaps)

1. **The three bypass strings are now restated verbatim in five shipped documents** — `README.md:176-178`,
   `SKILL.md:87-88`, `references/executors.md:79-80`, `references/recovery-loop.md:121-122`,
   `references/providers.md:71,94,137,222-224` — plus `scripts/resolve_stage.py:82-86`, and no test
   binds any document to the constant. They agree today (checked by grep). This is the same
   duplication shape T45 spent a task removing for the no-diff contract, reintroduced by T44 for the
   flags, and it is the shape that produced round 6's blocker. The halt vocabulary got a parity test
   after it drifted once (`scripts/test_unit_docs_parity.py`); these have not drifted yet.
2. **`resolve_stage.check_effort` is unreachable as a rejector** through the config path (proof under
   M9, §6). It is exercised only by direct calls in `EffortRejection`
   (`scripts/test_unit_resolve_stage.py:249-271`). LOOP-05 AC 2 is satisfied by `scripts/_config.py:88-99`;
   the resolver's copy is a latent guard.
3. **Round 6's observation 1 is empirically false, harmlessly.** It said "no supported provider
   daemonises". `cursor-agent -p` leaves a detached `node … worker-server` behind: I caught one
   (ppid 1) after my probe. It does **not** reproduce round 5's blocker — `lsof` shows its stdin,
   stdout and stderr all on `/dev/null`, so it cannot hold the driver's pipe open, and it stays in
   the process group `_spawn.py` created (pgid 52667 in my capture), so an expiry's `killpg` reaches
   it. I killed it; the sweep is clean.
4. **`loop.sh` records nothing when a respawn exits non-zero for any reason other than the timeout.**
   `scripts/loop.sh:214-218` converts 124 into `--halt executor`; `:219-220` turns everything else
   into `die 2` with only stderr, and `resolve_stage.py` never checks installation, so a missing CLI
   reaches the same path. Documented design (`scripts/loop.sh:18-22`), unchanged this round, and now
   also reachable via Gap 1.
5. **Spec edge case "provider CLI not installed ⇒ halt naming the command"** is therefore satisfied
   by the agent path (`references/recovery-loop.md:93`, `references/executors.md:233-243`) and not
   by the shell driver. Pre-existing.
6. **LOOP-07's only evidence lives outside the published artifact.** The three-option offer is in
   `<skills-dir>/tlc-spec-driven/references/sub-agents.md:40-50`, and that directory is not a git
   repository (`git rev-parse` there: *fatal: not a git repository*). Publishing `tlc-loop` does not
   deliver the hook, and `README.md` does not tell an installer their `tlc-spec-driven` needs it,
   while `SKILL.md:3` states as fact that "Another skill reaches it when tlc-spec-driven delegates
   Execute to loop mode." The spec scopes the edit in (`spec.md:35`). Unchanged from round 6.
7. **`README.md:196`'s "thirteen"** matches my count for P1 and excludes the 2 P2 review-only
   criteria (§2). Substantively accurate; arithmetically dependent on how partials are split.
8. **`cursor`'s `--force` is "allow unless explicitly denied"**, so an operator's
   `~/.cursor/cli-config.json` `permissions.deny` list still applies. A denied command is refused,
   not prompted, so it cannot hang a run — but cursor's bypass is the one of the three that is not
   absolute. Not documented; not a hazard.

---

## 8. Code Quality

| Check | Pass? |
| --- | --- |
| No features beyond what was asked | ✅ T44 is a 5-entry dict and three one-token argv changes; T45 removes text; T46 adds two helpers |
| No abstractions for single-use code | ✅ `NON_INTERACTIVE` is data, not a class; `reap()`/`matching()` are two module functions |
| No unnecessary flexibility | ✅ `reap(grace=…)` is parameterised only so the constant has one home |
| Only touched files required for the task | ✅ `17fe800..HEAD` is 16 files, all named in T44–T46 or their documentation obligations |
| Didn't "improve" unrelated code | ✅ |
| Matches existing patterns/style | ✅ same `#:` data comments, same docstring-as-rationale, same test-class-per-behaviour |
| Would a senior engineer approve? | ✅ — with Gap 1 raised in review, not blocking |
| Tests map to ACs and are non-shallow | ✅ `NonInteractiveDispatch` writes its expected values out literally rather than reading the resolver's table, and says why (`scripts/test_unit_resolve_stage.py:133-135`) |
| Spec-anchored outcome check | ✅ LOOP-05 AC 1's adapter table is now fully implemented and fully pinned |
| Per-layer coverage expectation | ✅ unit + integration + real-sibling-validator (`test_int_tlc_validators.py`) |
| Every test maps to a spec AC / edge case / Done-when | ✅ the four new tests cite T44's Done-when in the class docstring; no unclaimed tests found |
| Documented project guidelines followed | ✅ `tasks.md` Gate Check Commands; none other declared |

---

## 9. Edge Cases

- [x] Not a git repository → refused at bootstrap — `scripts/test_unit_init_loop.py:136-144`
- [x] `tasks.md` missing or failing `validate_tasks.py` → refused and named — `:145-156`, and the real validator at `scripts/test_int_tlc_validators.py:191-294`
- [x] Duplicated `Task:` trailer → counted once, ambiguity reported — `scripts/test_unit_gitio.py:104-137`, `scripts/test_unit_detect_phase.py:410-447`
- [ ] Uncommitted changes mapping to no task → halt and ask — prose only (`references/recovery-loop.md:96`)
- [ ] An executor commits despite the ban → phase stays open, work preserved — prose only (`references/executors.md:39-47`)
- [ ] A batch worker reports a failure → next batch does not start — prose only (`SKILL.md:244-245`, `references/executors.md:146-147`)
- [x] `.specs/loop.config.toml` absent → documented defaults — `scripts/test_unit_config.py:74-102`, `scripts/test_unit_init_loop.py:237-242`
- [~] Provider CLI not installed → halt naming the command — agent path prose; shell driver exits 2 without recording (§7 obs. 4–5)

---

## 10. Publication Readiness

| Check | Result |
| --- | --- |
| `README.md:37-42` install verification snippet | ✅ run verbatim: prints the sibling `tlc-spec-driven` directory, exit 0 |
| `README.md:62` dry-run detect | ✅ `phase=V action=verify round=1`, exit 0, porcelain unchanged |
| `README.md:101` config check | ✅ `ok 4 stage(s) resolve`, exit 0 |
| `README.md:202-204` dev commands | ✅ 396 full / compileall + `bash -n` clean |
| `README.md:52` quick-start invocation, `:117` shell driver | ✅ names that exist (`SKILL.md` frontmatter `name: tlc-loop`; `scripts/loop.sh` present and `bash -n` clean) |
| `LICENSE` ↔ `README.md:216` ↔ `SKILL.md:4` frontmatter | ✅ all CC-BY-4.0 (`LICENSE:1` "Creative Commons Attribution 4.0 International (CC BY 4.0)") |
| Credential-shaped strings | ✅ none — swept the tracked set for `sk-*`, `ghp_*`, `AKIA*`, `xox[baprs]-`, `glpat-`, `BEGIN … PRIVATE KEY`, and `(api_key\|secret\|password\|token) = "…"`. One hit, a false positive: `scripts/test_unit_spawn.py:102` `"tlcspawn%d" % os.getpid()` |
| Operator's environment exposed | ✅ **fixed this round** — round 6's report leaked the absolute home path in three places (`validation.md:167,450,502`); this report uses `<skills-dir>`. No other tracked file contains `/Users/…` or a username |
| `.gitignore` ↔ reality | ✅ `.specs/features/**/loop.json` ignored; `git ls-files` tracks none |
| Done-signature identical everywhere it is quoted | ✅ five shipped files, one string |
| `README.md` "Known limitations" honest | ✅ all five true; "thirteen ACs are prose" reconciled in §2; the approval bullet is accurate and is the strongest thing in the file — see Gap 2 for what it omits |
| Nothing in `README.md`/`SKILL.md`/`references/`/`.specs/` misleads a first-time reader | ✅ every claim I checked against code held. Gap 2 is an omission, not a misstatement |
| No leftover processes after this validation | ✅ swept: no `tlcspawn`/`_spawn.py`/`probe.py`/`sleep 600`; the one `cursor-agent worker-server` my probe leaked was killed and re-swept clean |
| Sensor isolation | ✅ worktree removed; `git status --porcelain` byte-identical to the pre-sensor baseline; HEAD `e3038d2` unchanged |

---

## 11. Requirement Traceability Update

| Requirement | Previous (round 6) | New |
| --- | --- | --- |
| LOOP-01 | ✅ Verified | ✅ Verified |
| LOOP-02 | ⚠️ code verified, documentation defect | ✅ **Verified** — the no-diff contract has one description and it matches the code |
| LOOP-03 | ✅ Verified (prose) | ✅ Verified (prose) |
| LOOP-04 | ✅ Verified | ✅ Verified |
| LOOP-05 | ❌ Needs Fix | ✅ **Verified** — the adapter table is fully implemented, pinned family-wide, and confirmed against three live CLIs |
| LOOP-06 | ✅ Verified | ✅ Verified — Gap 1 is a rare error-handling omission on the expiry path, not an AC failure |
| LOOP-07 | ⚠️ satisfied by review | ⚠️ Satisfied by review; evidence outside the published repository (§7 obs. 6) |

---

## 12. Follow-ups (none blocking)

### Follow-up 1 — handle every errno the group signal can raise (Minor)

- **Root cause**: `scripts/_spawn.py:57-62` catches only `ProcessLookupError`, and `:70-81`
  signals `proc.pid` after `proc.wait(timeout=grace)` may already have reaped it.
- **Fix**: catch `OSError` in `_signal_group`, and skip the escalation entirely when
  `proc.wait(timeout=grace)` returned rather than raised — the group is empty in exactly that case.
  Assert that an expiry never exits with anything but `TIMED_OUT`.
- **Priority**: Minor.

### Follow-up 2 — say what the native-agent path does about prompts (Minor)

- **Root cause**: the approval hazard is documented for `command` executors only, and the default
  configuration under the primary documented harness uses the `agent` path.
- **Fix**: one bullet in `README.md`'s "Known limitations" and one sentence in `SKILL.md:85-93`.
- **Priority**: Minor.

### Follow-up 3 — assert the consolidation, not the phrasings (Minor)

- **Root cause**: T45 replaced a phrase scanner with a structural rule and left the rule unasserted;
  M11 survives.
- **Fix**: assert that exactly one shipped document contains the canonical section and that every
  other file mentioning the mechanism links to `#the-no-diff-contract`. Add `records no commit` to
  `RETIRED_MECHANISM_CLAIMS` as T45's own docstring instructs for already-shipped phrasings.
- **Priority**: Minor.

---

## Summary

**Overall**: ✅ Ready to publish — 0 blockers, 0 majors, 3 minors

**Spec-anchored check**: 24/39 ACs traced to an assertion targeting the spec-defined outcome;
12 prose or review-only (10 P1 + 2 P2); 3 partial (LOOP-05 AC 5, LOOP-06 AC 1, LOOP-06 AC 2)
**Gate**: 396 passed, 0 failed, 0 skipped — twice (392 → 396, +4, none removed, none weakened)
**Sensor**: 15 mutations injected, 12 killed, 3 survived (1 provably equivalent, 1 documentation,
1 test scaffolding) — expanded depth, 10 of 15 aimed at `NON_INTERACTIVE` and the command builders
**Diff range**: `12bd8c3..e3038d2`; new this round `17fe800..e3038d2`

**What works**: Every command executor now carries a bypass that exists in its own CLI's `--help`
*and* is accepted by its real parser, on every invocation, under environment-detected harnesses
rather than only under a test flag — including the claude command path that Claude Code hides. The
risk that buys is stated in the first bullet of the README's limitations, in a Critical rule, and
in three references, in plain language. The no-diff contract has exactly one description, twelve
pointers, no self-contradiction, and a corrected counter sentence I traced through
`checkpoint.py` → `SKILL.md` → `update_loop.py` rather than taking on trust. The suite leaves no
probe behind. Rounds 5 and 6's overnight-killers are both closed. Ten of ten mutations aimed at the
new dispatch code died, including the conditional-bypass and unpinned-provider shapes that nothing
would have caught before T44.

**Issues found**: three minors, all recorded as follow-ups — an unhandled `PermissionError` class
in the kill escalation, observed once in 33 runs and unreproducible in 1000+ further attempts; an
approval hazard documented for the `command` path and unmentioned for the `agent` path the default
configuration uses; and a surviving documentation mutant showing T45's structural fix is held by
discipline rather than by a check.

**Next steps**: publish. Route the three follow-ups to a later `fix` round; none of them changes
what a user gets tonight.
