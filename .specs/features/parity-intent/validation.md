# Parity Guards Prove Intent Validation

**Date**: 2026-08-11
**Spec**: `.specs/features/parity-intent/spec.md`
**Diff range**: `main...HEAD` = `928f53e..a82c10e` (4 commits) on `fix/parity-guards-prove-intent`
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Validation: FAIL

The four headline probes are genuinely fixed and no pre-existing guard was
weakened. The verdict is FAIL on **spec-anchored AC completeness**: two stated
acceptance criteria (P1 AC 5, P1 AC 7) are implemented by code that provably
cannot fail, and one (P1 AC 4) holds only for the exact line-shape the shipped
corpus happens to use.

**Diff surface claim verified**: `git diff main...HEAD --name-only` returns
exactly `.specs/features/parity-intent/spec.md`,
`.specs/features/parity-intent/tasks.md`, `scripts/test_unit_docs_parity.py`.
**No shipped document changed.** ✅

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1 - `visible()` + rewire | ✅ Done | `scripts/test_unit_docs_parity.py:290`, all four guards read through `read_visible()` |
| T2 - fence-aware `section()` | ✅ Done | `scripts/test_unit_docs_parity.py:724`; but the shipped-doc P7 replay is a weaker probe than the one it claims (see P2 AC 3) |
| T3 - `fenced_commands()` | ✅ Done | `scripts/test_unit_docs_parity.py:780`, three guards fenced, H row left inline |
| T4 - `negated_by()` + vocabulary | ⚠️ Partial | `scripts/test_unit_docs_parity.py:756`; the clause rule (AC 5) has no discriminating test and the inline guard's negation check is inert (AC 7) |

---

## Spec-Anchored Acceptance Criteria

### P1: A guard rejects a document that does not instruct

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - ignore every `<!-- ... -->` span, incl. multi-line | every span removed | `scripts/test_unit_docs_parity.py:302` - `re.sub(r"<!--.*?(?:-->|\Z)", "", text, flags=re.DOTALL)`; `:680` - `assertEqual(visible("keep <!-- drop --> keep"), "keep  keep")`; `:683` - `assertEqual(visible("a\n<!-- one\ntwo\nthree -->\nb"), "a\n\nb")` | ✅ PASS |
| AC 2 - command only inside a comment ⇒ guard fails, naming the document | fail + document named | `scripts/test_unit_docs_parity.py:459` - `assertNotIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`; guard `:435-442`. Sensor P2 killed `test_the_halt_field_section_names_the_command` | ⚠️ Spec-precision gap - fails correctly, but the message names the **scope** (`"the `halt` field section"`, `:441`), never the document path |
| AC 3 - fenced-artifact guard fails when the command is prose-only | fail + document named | `scripts/test_unit_docs_parity.py:376` - `haystack = collapsed(fenced_commands(scope) if fenced else scope)`; `:597` - `assertNotIn("thing --flag", fenced_commands(self.DOC))`; `:624` - `assertNotIn(cmd, collapsed(fenced_commands(rescoped)))`. Sensor A10 killed the guard | ⚠️ Spec-precision gap - same naming caveat as AC 2 |
| AC 4 - negated introducing clause ⇒ guard fails, naming the marker | fail + marker named | `scripts/test_unit_docs_parity.py:383` - `marker = negated_by(scope, command)` / `:384` - `assertIsNone(marker, ...{marker!r}...)`; `:521` - `assertEqual(negated_by(body, self.COMMAND), "never run")`; `:531` - same for P1b. Sensor P1/P1b killed `test_the_halt_phase_names_the_command` | ❌ GAP - holds only for a backslash-continued command. Sensor A7: a **one-line** command with `never run:` directly above leaves the guard green (see Gap 2) |
| AC 5 - read only the clause after the final `". "` | an earlier sentence's wording cannot flag a correct instruction | `scripts/test_unit_docs_parity.py:772` - `clause = " ".join(lines[max(0, number - 4):number]).lower().rsplit(". ", 1)[-1]`; test `:535-545` - `assertIsNone(negated_by(body, "...--halt executor"))` | ❌ GAP - vacuous. Sensor H8 survived; the assertion holds for window widths 3-20 with and without the clause split, and for an **empty** vocabulary (see Gap 1) |
| AC 6 - vocabulary is verb-specific **and** flags no shipped fence | 0 offenders; only verb-specific markers | flags-none: `scripts/test_unit_docs_parity.py:580` - `assertEqual(offenders, [], ...)`, independently re-derived → 0 offenders. verb-specific: `:561` - `assertIn(marker.split()[-1], IMPERATIVE_VERBS, marker)` | ⚠️ Split - the "flags none" half is real and sensitive; the "verb-specific" half is **tautological** (`NEGATED_IMPERATIVES` is built from `IMPERATIVE_VERBS` by comprehension at `:749-753`). Sensor H10 survived |
| AC 7 - inline guard applies criteria 1, 2, 4 and does **not** require a fence | negation still rejected on the inline mention | `scripts/test_unit_docs_parity.py:426` - `read_visible(...)` (crit. 1-2 ✅); `:432` - `fenced=False` (no fence required ✅); `:383` - `negated_by(scope, command)` (crit. 4 wired) | ❌ GAP - criterion 4 is **structurally inert**. `table_row()` (`:817`) returns one line, and `negated_by`'s clause window `lines[n-4:n]` is empty at `n=0`, so it always returns `None`. Sensor A8 survived (see Gap 3) |

### P2: A fenced `#` does not truncate a scope

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - section scan ignores lines inside fences | fenced lines skipped when locating the terminator | `scripts/test_unit_docs_parity.py:724-728` - `fenced = _fenced(lines)` / `if number in fenced: continue`; `:646` - `assertIn("more first-section text", body)`. Sensor H3 killed | ✅ PASS |
| AC 2 - section still extends to the next real heading | scope reaches the next real heading, stops there | `scripts/test_unit_docs_parity.py:650` - `assertNotIn("## second", body)`; `:654` - `assertIn("# not a heading", section(self.DOC, "## first", "fake.md"))`. Sensor H3/H9 killed | ✅ PASS |
| AC 3 - guards inside such a section still pass on the shipped documents | Phase H guard passes, scope still ends at `### Step 3` | `scripts/test_unit_docs_parity.py:669` - `assertIn(cmd, collapsed(fenced_commands(body)))` and `:673` - `assertNotIn("### Step 3", body)` | ⚠️ Spec-precision gap - behaviour is correct (sensor P7 with a true column-0 `#` survives), but the test injects an **indented** `   # resolve the cause first` (`:662`), which already passed under `main`'s `section()`. It is not a replay of P7 (see Gap 4) |

**Status**: ❌ Gaps present - 3 ❌ GAP, 4 ⚠️ spec-precision, 3 ✅ PASS across 10 criteria.

---

## Edge Cases

- [x] **Unterminated `<!--` hides the remainder** - `scripts/test_unit_docs_parity.py:302` (`(?:-->|\Z)`); `:688` - `assertEqual(visible("shown\n<!-- swallowed\nalso swallowed"), "shown\n")`. Sensor H1/H2 killed.
- [x] **Command in a comment *and* in a live fenced block ⇒ pass** - `scripts/test_unit_docs_parity.py:468` - `assertIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`. Sensor H2 killed.
- [x] **No fenced block at all ⇒ fail, not raise** - `scripts/test_unit_docs_parity.py:794-797` returns `""`; `:603` - `assertEqual(fenced_commands("## s\n\njust prose, no block\n").strip(), "")`; end-to-end path exercised by sensor A10. ⚠️ the "names the document" half is the same scope-vs-path caveat as AC 2/3.
- [x] **Negated fence + a second affirmative instance ⇒ pass** - `scripts/test_unit_docs_parity.py:551-555` appends a real fenced affirmative copy, `:556` - `assertIsNone(negated_by(rescued, self.COMMAND))`. Sensor H6 killed. ⚠️ but sensor A9 shows an affirmative instance in **prose** also rescues, which AC 3 says must not count as an instruction (Gap 5).
- [x] **Vocabulary matches no fence in any shipped document, asserted by a test** - `scripts/test_unit_docs_parity.py:565-584`, `assertEqual(offenders, [], ...)`. Independently re-derived: 0 offenders with the shipped vocabulary, 15 offenders with a bare-negation-word list - the verb-specific choice is measured and correct.

---

## Discrimination Sensor

**Isolation**: detached `git worktree add --detach` at `a82c10e`, removed with
`git worktree remove --force`. Real tree `git status --porcelain` was **empty
before and empty after**; `git worktree list` shows only the primary tree. No
`git stash` used. Sensor run is valid.

### Original probes from `.specs/features/halt-resume/validation.md`

| # | Mutation | Expect | Result | Guard under test failed? |
| - | -------- | ------ | ------ | ------------------------ |
| P1 | Phase H intro → `"Never run this, it is not a supported operation:"` | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P1b | Phase H intro → `"A human deletes \`loop.json\` and starts over. Whatever you do, never run:"` | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P2 | `## \`halt\`` block wrapped in an HTML comment | kill | ✅ Killed | **YES** - `test_the_halt_field_section_names_the_command` |
| P7 | column-0 `# resolve the cause first` inside the Phase H fence | **survive** | ✅ Survived | n/a - false-positive direction, correctly no longer fails |

### Attacks on the new helpers (document mutations)

| # | Mutation | Expect | Result | Guard failed? |
| - | -------- | ------ | ------ | ------------- |
| A1 | negation outside the vocabulary: `"This call was removed in 0.4, it will error:"` | kill | ⚠️ Suite red, **guard green** | NO - accepted residual risk, recorded at `spec.md:47` and `scripts/test_unit_docs_parity.py:496-500` |
| A2 | Phase H fence opened, closing ``` deleted | kill | ⚠️ Suite red, **guard green** | NO - caught only by `test_each_scope_excludes_the_passage_that_follows_it`; `_fenced()` has no unterminated-fence rule (Gap 6) |
| A3 | command split across two adjacent fences | kill | ⚠️ Suite red, **guard green** | NO - `fenced_commands()` concatenates all fence bodies (Gap 7) |
| A4 | Phase H fence switched `` ``` `` → `~~~` (valid CommonMark) | kill | ✅ Killed | YES - `_fenced()` only knows `` ``` ``; false-positive direction, low risk (repo uses `` ``` `` exclusively) |
| A5 | instruction withdrawn; command parked in a "changelog example" fence | kill | ⚠️ Suite red, **guard green** | NO - same residual-risk class as A1 |
| A6 | `<!--` inside a bash string in the Phase H fence | **survive** | ❌ **Killed** | **YES** - false positive; `visible()` strips comments inside fences (Gap 8) |
| A7 | **one-line** command with `never run:` directly above | kill | ⚠️ Suite red, **guard green** | NO - **Gap 2**, AC 4 defeated |
| A8 | H transition row → `never run update_loop.py --resume` | kill | ❌ **Survived** | NO - **Gap 3**, AC 7 criterion 4 inert |
| A9 | negated fence rescued by an affirmative **prose** mention | kill | ⚠️ Suite red, **guard green** | NO - **Gap 5** |
| A10 | whole Phase H block moved into prose (no fence) | kill | ✅ Killed | YES - `test_the_halt_phase_names_the_command` |

### Helper-logic mutations

| # | Mutation (`scripts/test_unit_docs_parity.py`) | Result | Killed by |
| - | --------------------------------------------- | ------ | --------- |
| H1 | `visible()` → `return text` (no-op) | ✅ Killed | 5 tests incl. `test_a_commented_out_block_does_not_count_as_documentation` |
| H2 | `visible()` → `return ""` | ✅ Killed | 19 tests |
| H3 | `section()` → `fenced = set()` | ✅ Killed | `test_a_fenced_hash_does_not_end_the_section`, `test_the_fenced_line_is_still_part_of_the_section` |
| H4 | `fenced_commands()` → `return text` | ✅ Killed | `test_a_scope_with_no_fence_yields_nothing`, `test_prose_outside_a_fence_is_not_an_instruction`, `test_moving_the_command_into_prose_fails_the_guard` |
| H5 | `negated_by()` → `return None` always | ✅ Killed | `test_a_never_run_lead_in_is_caught`, `test_an_inverted_instruction_is_caught` |
| H6 | `negated_by()` → keep marker despite an affirmative occurrence | ✅ Killed | `test_an_affirmative_copy_rescues_a_negated_one` |
| H7 | `NEGATED_IMPERATIVES = ()` | ✅ Killed | `test_a_never_run_lead_in_is_caught`, `test_an_inverted_instruction_is_caught` |
| H8 | negation window widened from the clause to a 3-line window | ❌ **Survived** | — **Gap 1**, AC 5 vacuous |
| H9 | `section()` bound `depth <= level` → `depth == level` | ✅ Killed | `test_each_scope_excludes_the_passage_that_follows_it` |
| H10 | `IMPERATIVE_VERBS` → `("run",)` | ❌ **Survived** | — 12 of 15 markers unexercised |

### Pre-existing guards (regression - did this feature weaken anything?)

| # | Mutation | Result | Killed by |
| - | -------- | ------ | --------- |
| R1 | drop `blast_radius` from the SKILL.md halt-reason list | ✅ Killed | `test_skill_md_enumerates_exactly_the_implemented_reasons` |
| R2b | reintroduce the retracted claim `"disposable"` in `state-schema.md` | ✅ Killed | `test_no_shipped_document_repeats_a_retracted_claim` |
| R3 | unmarked `no_diff_tasks` mention added to `README.md` | ✅ Killed | `test_every_documented_mention_of_no_diff_tasks_is_marked_legacy` |
| R4 | remove `strict_routing` from `config-schema.md` | ✅ Killed | `test_config_docs_describe_domain_stages_and_strict_routing` |
| R5 | drop `$tlc-loop` from the routing contract | ✅ Killed | `test_the_tasks_handoff_is_self_contained` |
| R6 | reintroduce `clearing \`halt.reason\`` in the H row | ✅ Killed | `test_no_shipped_document_sends_the_reader_to_the_field`, `test_the_transition_row_names_the_command` |
| R7b | change `stages.backend` model in the README quick start | ✅ Killed | `test_the_quick_start_example_agrees_on_every_stage_it_shows` |
| R8 | move the `--gate-attempt` call out of Phase B | ✅ Killed | `test_skill_md_names_the_call_that_records_a_failed_gate`, `test_the_call_sits_in_the_phase_that_runs_the_gate` |

**No pre-existing parity check was weakened: 8/8 regression mutants killed.**

**Sensor depth**: P0-full (32 mutations)
**Result**: 24 behaved as expected; **4 unexpected** (A6 false positive, A8 / H8 / H10 survived), **6 partial** (A1, A2, A3, A5, A7, A9 - suite red only via probe-anchor tests, the guard itself stayed green) - **FAIL**

---

## Gate Check

- **Gate command**: `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Exit code**: **0**
- **Result**: **601 passed, 0 failed, 0 skipped** (212.3s)
- **Test count before feature** (`main`, `700436c`): 496 unit; parity module 35
- **Test count after feature** (`a82c10e`): 519 unit; parity module 58; 601 total
- **Delta**: **+23 unit tests**, all inside `scripts/test_unit_docs_parity.py`
- **Tests deleted**: none. **Assertions weakened**: none - see below.

---

## Weakening Analysis (`main` vs `HEAD`, the four guard bodies)

| Guard | Change | Direction |
| ----- | ------ | --------- |
| `test_the_transition_row_names_the_command` (`:424`) | `read_shipped` → `read_visible`; bare `assertIn` → `assert_instructs(..., fenced=False)` | Stronger (comments stripped, negation check added) - but the negation check cannot fire (Gap 3) |
| `test_the_halt_field_section_names_the_command` (`:435`) | + `read_visible`, + `fenced_commands`, + `negated_by` | **Strictly stronger** |
| `test_the_halt_phase_names_the_command` (`:444`) | + `read_visible`, + `fenced_commands`, + `negated_by` | **Strictly stronger** |
| `test_the_call_sits_in_the_phase_that_runs_the_gate` (`:842`) | + `read_visible`, + `fenced_commands`, + `negated_by` | **Strictly stronger** |
| `section()` (`:703`) | `text.find(heading)` → line-start match; fenced lines skipped | Heading match stronger; fenced-skip is a deliberate relaxation matching P2 AC 1. The bound test at `:470-486` still holds (H9 killed) |

`assert_instructs()` **did not drop an assertion** - it adds one. Message
quality is a near-wash: the new messages name the missing command verbatim
(an improvement over `"does not carry the command that clears it"`), but lose
the per-guard rationale prose (e.g. `"naming the flag in passing is not the
same thing"` at old `:414`). The `where` argument carries the surviving
context. Not a defect.

**Vacuous/tautological tests found**: `test_the_vocabulary_is_verb_specific`
(`:558-563`) - cannot fail, since `NEGATED_IMPERATIVES` is generated from
`IMPERATIVE_VERBS` at `:749-753`. `test_a_negation_in_an_earlier_sentence_does_not_flag`
(`:535-545`) - passes under every window width and under an empty vocabulary.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ four small helpers, `_fenced()` reused not reimplemented |
| Surgical changes | ✅ one file touched; no shipped document changed |
| No scope creep | ✅ prose scans left alone per `spec.md:33` |
| Matches patterns | ✅ module-level helpers + docstring-as-rationale, consistent with the file |
| Spec-anchored outcome check | ❌ AC 5 and AC 7 assert outcomes their code cannot produce |
| Per-layer Coverage Expectation met | ⚠️ matrix requires "every branch"; `negated_by`'s multi-occurrence path and 12 of 15 vocabulary markers are unexercised (H10) |
| Every test maps to a spec requirement | ✅ no unclaimed tests |
| Documented guidelines followed | ✅ none exist - strong defaults applied (per `tasks.md:19`) |

---

## Fix Plans

### Gap 1 (Major) - AC 5 is vacuous, and its stated rationale is false

- **Root cause**: `spec.md:48` and the docstring at `scripts/test_unit_docs_parity.py:759-761` justify the clause split with *"a 3-line window flags `SKILL.md:237`"*. It does not: `SKILL.md:235` says **"do not retry"**, and `retry` is not in `IMPERATIVE_VERBS` (`:747`), so no window width can ever flag it. Re-derived independently: for all four shipped scopes, windows of 3/4/6/10/20 lines with and without the clause split all return `None`.
- **Fix task**: either (a) drop the clause split and keep the window, simplifying `:772`, or (b) keep it and add a test that actually distinguishes the two - a fixture whose earlier sentence contains a real vocabulary marker (e.g. `"Never use the editor. Lift the halt with:"`) asserted `None` under clause-scope. Correct the false claim at `spec.md:48`.
- **Priority**: Major

### Gap 2 (Major) - AC 4 fails for a one-line command

- **Root cause**: `scripts/test_unit_docs_parity.py:772` anchors the clause window to the **scan window start** (`lines[n-4:n]`), not to the command's own line, and `:774-775` returns `None` on the first matching window with a clean clause. For a command on a single line `L`, the earliest matching window starts at `L-2`, so its clause window `lines[L-6:L-2]` excludes the fence opener *and* the introducing clause. Verified directly: negation directly above a one-line command → `negated_by` returns `None`; the two-, three-line and blank-line-gap variants are all caught. The guard works today only because both shipped commands use a backslash continuation.
- **Fix task**: anchor the clause window to the line where the command's **first** token appears, and scan all occurrences before deciding, rather than short-circuiting on the earliest window.
- **Priority**: Major

### Gap 3 (Major) - AC 7's negation criterion is inert on the inline guard

- **Root cause**: `table_row()` (`:817`) returns exactly one line; `negated_by`'s clause window at `:772` is `lines[max(0,n-4):n]`, which is empty at `n=0`. The call at `:383` therefore always yields `None` for the H transition row. Sensor A8 (`| \`H\` | ... never run update_loop.py --resume |`) passes the whole suite - the same inverted-instruction failure mode as P1b, on the one guard `spec.md:75` singles out.
- **Fix task**: make `negated_by` also read the text **preceding the command on its own line**, then add a test that the H row rejects an inline negated mention.
- **Priority**: Major

### Gap 4 (Minor) - P2 AC 3's shipped replay is not a replay of P7

- **Root cause**: `scripts/test_unit_docs_parity.py:662` injects `   # resolve the cause first` (3-space indent). `main`'s `section()` searched for `"\n" + "#"*d + " "`, so an indented `#` never truncated anything - re-ran both: indented variant PASSes on `main` **and** on `HEAD`; column-0 variant FAILs on `main` and PASSes on `HEAD`. The behaviour is fixed (sensor P7 confirms), but this test does not evidence it and would still pass if `section()` regressed for indented input.
- **Fix task**: change `:662` to inject the comment at column 0.
- **Priority**: Minor

### Gap 5 (Minor) - an affirmative *prose* mention rescues a negated fence

- **Root cause**: `assert_instructs` (`:376`) narrows the presence check to `fenced_commands(scope)` but passes the **unfenced** `scope` to `negated_by` at `:383`. A document whose only fenced instruction is negated, but which mentions the command affirmatively in prose, passes (sensor A9). AC 3 says prose is not an instruction; the negation path does not honour that.
- **Fix task**: run the "is there an un-negated occurrence" search over the fenced text when `fenced=True`.
- **Priority**: Minor

### Gap 6 (Minor) - `_fenced()` has no unterminated-fence rule

- **Root cause**: `_fenced()` (`:924-934`) toggles on each `` ``` `` and never reconciles an odd count, so an unclosed fence marks the rest of the document as fenced - `section()` runs to EOF and `fenced_commands()` accepts a command from any later section. `visible()` handles the analogous unterminated-comment case explicitly (`:302`). Sensor A2 is caught today only incidentally, by `test_each_scope_excludes_the_passage_that_follows_it`.
- **Fix task**: decide and record the intended behaviour for an odd fence count; add the edge case to `spec.md`.
- **Priority**: Minor

### Gap 7 (Cosmetic) - `fenced_commands()` concatenates all fences in a scope

- **Root cause**: `:794-797` joins every fence body, so `collapsed()` can assemble one command from two separate fences (sensor A3). Requires a contrived document.
- **Priority**: Cosmetic

### Gap 8 (Minor) - `visible()` strips HTML comments inside code fences

- **Root cause**: `:302` runs over the whole text with no fence awareness. A bash example containing `<!--` silently deletes a span, and an unpaired `<!--` deletes the rest of the document - the same false-positive class this feature exists to remove (P7). Sensor A6 turns a valid document red. Confirmed **no shipped document currently has `<!--` inside a fence**, so this is latent.
- **Fix task**: skip `_fenced()` lines in `visible()`, or add a test pinning the current behaviour as intended.
- **Priority**: Minor

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| INTENT-01 (P1 AC 1, 2 - HTML comments) | Implementing | ✅ Verified |
| INTENT-02 (P1 AC 3, 7 - fence required / inline exempt) | Implementing | ❌ Needs Fix - AC 7 criterion 4 inert (Gap 3) |
| INTENT-03 (P1 AC 4, 5, 6 - negation vocabulary) | Implementing | ❌ Needs Fix - Gaps 1, 2 |
| INTENT-04 (P2 AC 1, 2, 3 - fence-aware section) | Implementing | ✅ Verified (test-quality note: Gap 4) |

---

## Summary

**Overall**: ⚠️ Issues - the feature does what its Success Criteria claim, but three acceptance criteria are not met as written.

**Spec-anchored check**: 3/10 ✅ PASS, 4 ⚠️ spec-precision, 3 ❌ GAP
**Sensor**: 32 mutations - 24 as expected, 4 unexpected, 6 partial (guard green while the suite went red for unrelated reasons)
**Gate**: 601 passed, 0 failed, exit 0

**What works**:

- Probes P1, P1b and P2 now kill the guard they were aimed at - confirmed at guard level, not merely suite level.
- Probe P7 no longer fails a harmless edit, verified with a true column-0 `#`.
- The negation vocabulary flags 0 shipped fences; a bare-negation-word list would flag 15. The verb-specific choice is measured and right.
- No shipped document changed; no pre-existing parity check weakened (8/8 regression mutants killed); +23 tests, none deleted.
- `visible()`, `section()`, `fenced_commands()` and the core of `negated_by()` are all individually discriminating (H1-H7, H9 killed).

**Issues found**: Gaps 1-8 above, ranked. The three Major gaps all sit in `negated_by()`'s clause-window arithmetic and the AC 5 rationale.

**Next steps**: route Gaps 1, 2 and 3 to fix tasks; Gaps 4-8 are optional hardening. Re-verify after the fixes.
