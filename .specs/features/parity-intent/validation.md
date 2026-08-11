# Parity Guards Prove Intent Validation

**Spec**: `.specs/features/parity-intent/spec.md`
**Verifier**: independent sub-agent (author ≠ verifier), rounds 1, 2 and 3

| Round | Date | Range | Verdict |
| ----- | ---- | ----- | ------- |
| 1 | 2026-08-11 | `928f53e..a82c10e` | FAIL - 8 ranked gaps |
| 2 | 2026-08-11 | `a82c10e..3821649` (fix commit, test-only) | FAIL (narrow) - 5/5 claimed fixes verified, 2 Major test-integrity gaps survive |
| 3 | 2026-08-11 | `3821649..9a6a9ba` (fix commit, test-only) | **PASS** - both Major gaps closed at guard level; 4 Minor survivors, none blocking |

---

## Validation: PASS

**Round 3, final bounded iteration.** Both Major gaps round 2 raised are
genuinely closed, verified at *guard* level with fresh attacks rather than by
re-reading the diff:

1. `test_a_nearby_negation_about_something_else_does_not_flag`
   (`scripts/test_unit_docs_parity.py:535-554`) is **falsifiable**. Four
   independent mutations kill it (`G1`, `G4`, `F10`, `M15`), and the two that
   *should not* kill it - emptying the vocabulary (`G2`) and widening
   `INTRO_LINES` to 20 (`G3`) - correctly do not. The precondition added at
   `:549-553` is what carries the proof: the needle now has to match a fence
   before the `assertIsNone` at `:554` is allowed to mean anything.
2. `test_the_vocabulary_flags_no_fence_in_any_shipped_document` (`:677-698`)
   now **runs the code it guards**. Round 2's headline demonstration is
   reversed: `V1` (adding `"commit"` to `IMPERATIVE_VERBS`) made production flag
   `SKILL.md` while the net reported zero; at this commit the same mutation
   **fails the net by name**. `M2` (`INTRO_LINES` 4 -> 10), which survived the
   whole round-2 suite, is likewise killed by the net now.

Round-2 minor gaps E and F are closed as well. C, D and G survive and are
Minor/Cosmetic test-coverage holes with correct behaviour underneath. Round-1
Gaps 6, 7 and 8 remain latent at **0 shipped occurrences each**, and 6 and 8 are
now recorded in `spec.md`'s Out of Scope table.

**Diff surface**: `git diff 3821649..9a6a9ba --name-only` = `.specs/LESSONS.md`,
`.specs/features/parity-intent/spec.md`, `.specs/features/parity-intent/validation.md`,
`.specs/lessons.json`, `scripts/test_unit_docs_parity.py`. **No shipped document
changed** across the whole branch (`git diff main..HEAD --name-only` touches
`.specs/` and the one test module only). Real tree `git status --porcelain`
empty before and after the sensor; `git worktree list` back to the primary tree;
no `git stash` used.

---

### Round-2 Gap Disposition

| Gap | Round-2 finding | Round-3 status | Evidence |
| --- | --------------- | -------------- | -------- |
| A (Major) | `test_a_negation_in_an_earlier_sentence_does_not_flag` unfalsifiable; carried the retracted claim | ✅ **Fixed** | Renamed and repaired at `:535-554`. Needle is now the collapsed form; `:549-553` `assertIn(command, collapsed(fenced_commands(body)))` proves it matches a fence before `:554` asserts anything. Sensors `G1` (add verb `retry`) and `G4` (negate the shipped Phase B intro) **kill the test**; `F10`, `M15`, `M10`, `M16` also kill it. The comment at `:536-543` no longer repeats the retracted window claim - `grep` for it over the module returns only accurate, explicitly-historical text |
| B (Major) | AC-6 corpus net reimplemented the scan; could report clean while production flagged | ✅ **Fixed** | `fence_intro()` `:895-904` is the single definition; `negated_by` `:926` and the net `:689` both call it. Sensor `V1` → **net fails by name** (round 2: silent). `M2` (4→10) → **net fails** (round 2: survived). `M2c` (4→8) → net fails. `M24` (widen **and** re-decouple the net) → survives, which is the control proving the coupling is what kills `M2`. `F6` (make `fence_spans` treat every fence line as an opening - the old net's third bug) → killed by 8 tests. Re-derived independently: the corpus has **162 fence marker lines but 81 openings**; SKILL.md alone is 30 and 15, matching the comment at `:682` |
| C (Minor) | Fence requirement unpinned through `assert_instructs` | ➖ **Not fixed** | `M23` (`:376` → `haystack = collapsed(scope)`) **survives** again. Behaviour is right and covered three ways - `A10` kills the guard, `:727-742` covers the helper, and the opposite mutation `F11` (haystack always fenced) is killed - but the presence half of `assert_instructs` still has no direct test. One `assertRaises` away |
| D (Minor) | Inline "preceding text" anchor unpinned | ➖ **Not fixed** | `M21` (`:932` `(line.split(command,1)[0], line)` → `(line, line)`) **survives**. New probe `D1` (a `never run` placed *after* the command in the shipped `H` row) also survives - out of scope by `spec.md:116`, which says *preceding*, so the behaviour is as specified; only the pin is missing |
| E (Minor) | `INTRO_LINES` had a floor but no ceiling | ✅ **Closed (bounded)** | The corpus net now supplies the ceiling. Measured through the production helpers: 0 offenders at widths 2-6, **1 at width 8** (`SKILL.md:102`, `never pass`), 2 at width 20. `M1` (4→3) killed by `:585-598`; `M2c` (4→8), `M2` (4→10), `M2b` (4→40) all killed by the net. `M2d` (4→5) survives - the corpus cannot distinguish 4 from 5-6, which is a property of the documents, not a hole in the check. `spec.md:40` states exactly this and is now true |
| F (Minor) | `fence_spans()`' unterminated branch unfalsifiable | ✅ **Fixed** | `test_an_unterminated_fence_runs_to_the_end` `:646-653` pins both halves: `:651` `assertEqual(fence_spans(lines), [(1, len(lines))])` and `:653` `assertEqual(negated_by(doc, "thing --flag"), "never run")` on an unterminated document. `M13` (delete `:890-891`) → **killed** (round 2: survived). The docstring claim at `:878-879` that `_fenced()` already assumes this was checked and is accurate |
| G (Cosmetic) | Inline branch's fence exclusion unpinned | ➖ **Not fixed** | `M22` (drop `number not in inside` at `:934`) **survives**. No shipped inline guard has a fence in its scope |

---

### Spec-Anchored Acceptance Criteria

All `file:line` refer to `scripts/test_unit_docs_parity.py` at `9a6a9ba` unless stated.

#### P1: A guard rejects a document that does not instruct

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - ignore every `<!-- ... -->` span, incl. multi-line | every span removed | impl `:302` `re.sub(r"<!--.*?(?:-->\|\Z)", "", text, flags=re.DOTALL)`; `:795` `assertEqual(visible("keep <!-- drop --> keep"), "keep  keep")`; `:798` `assertEqual(visible("a\n<!-- one\ntwo\nthree -->\nb"), "a\n\nb")`; `:815` `assertNotIn("<!--", stripped)`. Sensors `M9` (no-op) killed 5, `M10` (strip-all) killed 20 incl. all four guards, `F14` (drop `re.DOTALL`) killed 4 | ✅ PASS |
| AC 2 - command only inside a comment ⇒ guard fails, naming the document | fail + document named | `:459` `assertNotIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`. **All four guards now proven at guard level**: `P2` kills `test_the_halt_field_section_names_the_command`, `P2b` kills `test_the_halt_phase_names_the_command`, `P2c` kills `test_the_transition_row_names_the_command`, `P2d` kills `test_the_call_sits_in_the_phase_that_runs_the_gate` | ⚠️ Precision (carried, 3rd round) - fails correctly; the message at `:380` names the **scope** (`"the \`halt\` field section"`), not the document path |
| AC 3 - fenced-artifact guard fails when the command is prose-only | fail + document named | impl `:376` `haystack = collapsed(fenced_commands(scope) if fenced else scope)`; `:712` `assertNotIn("thing --flag", fenced_commands(self.DOC))`; `:739-742` `assertNotIn(cmd, collapsed(fenced_commands(rescoped)))`. Sensor `A10` (Phase H block de-fenced) → **guard killed**; `M12` killed by 3 tests; `F11` (haystack always fenced) killed by 2 | ⚠️ Precision - behaviour correct, `M23` still survives (Gap C) |
| AC 4 - negated introducing clause ⇒ guard fails, naming the marker | fail + marker named | impl `:383-388`; `:522` `assertEqual(negated_by(body, self.COMMAND), "never run")`; `:533` same for P1b; `:623` one-line variant; `:598` wrapped variant. Sensors `P1`, `P1b`, `N5`, `N7`, `N8` → **guard killed** in every case; `M4`/`M5` kill 10-11 tests | ✅ PASS |
| AC 5 - anchor the lookbehind to the command's own fence opener, or to the text preceding it on its line | anchored, not scan-relative | impl `:907-943`; fenced anchor `:925-928` via `fence_intro()` `:895-904`; inline anchor `:932`; `:623`, `:629`. **Non-vacuity**: `M19` restores the pre-fix scan-anchored + clause-split `negated_by` verbatim → kills 8 tests; `F1` (`fence_intro` → `""`) kills 9; `F2` (window narrowed by one) kills `:585`; `F4` (window read *below* the fence) kills 9; `M20` killed | ⚠️ Precision - the fenced half is strongly pinned; the inline half's "text **preceding** it" still is not (`M21`, `D1` survive) |
| AC 6 - vocabulary verb-specific **and** flags no shipped fence | 0 offenders; verb-specific only | verb-specific: `:570-574` `SPELLED_OUT` written out, `:583` `assertEqual(sorted(self.SPELLED_OUT), sorted(NEGATED_IMPERATIVES))`, `:579` `assertEqual(negated_by(doc, "thing --flag"), marker, marker)` for all 15 - `M3` kills both. flags-none: `:693-698` `assertEqual(offenders, [], ...)` computed at `:688-692` **through `fence_spans()` + `fence_intro()`**. Positive control `:600-616` asserts a bare-word list *does* flag, and `F16` (make the corpus iterator yield nothing) kills it, so the net is proven to be reading real text. Sensors `V1`, `M2`, `M2b`, `M2c`, `M20`, `P1`, `N5`, `N7`, `N8`, `G1`, `G3` all fail the net | ✅ PASS - round-2 Gap B closed |
| AC 7 - inline guard applies criteria 1, 2, 4; does not require a fence | negation rejected on the inline mention | `:426` `read_visible(...)` (crit 1-2, pinned by `P2c`); `:432` `fenced=False`; `:629` `assertEqual(negated_by(row, "update_loop.py --resume", fenced=False), "never run")`; `:635-644` `with self.assertRaises(AssertionError)`; `:664-668` affirmative row accepted, killed by `F10` and `F11`. Sensor `N6` → **guard killed**; `M7` kills `:635` | ✅ PASS |

#### P2: A fenced `#` does not truncate a scope

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - section scan ignores lines inside fences | fenced lines skipped when locating the terminator | impl `:839-843` `fenced = _fenced(lines)` / `if number in fenced: continue`; `:761` `assertIn("more first-section text", body)`. Sensor `M11` (`fenced = set()`) killed 3 tests | ✅ PASS |
| AC 2 - section still extends to the next real heading | reaches the next real heading, stops there | `:765-766` `assertNotIn("## second", body)` / `assertNotIn("other", body)`; `:769` `assertIn("# not a heading", section(...))`. Sensors `F12` (`depth <= level` → `depth < level`) and `F13` (invert the space check) **kill `:763-766`**; `M11`, `M15` kill the neighbours | ✅ PASS |
| AC 3 - guards inside such a section still pass on the shipped documents | Phase H guard passes, scope still ends at `### Step 3` | `:777` injects `"# resolve the cause first\n"` at column 0; `:784-787` `assertIn(cmd, collapsed(fenced_commands(body)))`; `:788` `assertNotIn("### Step 3", body)`. Sensor `P7` (column-0 `#` in the shipped file) **survives** - correct, no false positive; `M11`/`M15` kill this test | ✅ PASS |

**Status**: 7 ✅ PASS, 3 ⚠️ precision, 0 ❌ GAP across 10 criteria
(round 1: 3/4/3; round 2: 4/3/1).

---

### Edge Cases

- [x] **Unterminated `<!--` hides the remainder** - `:302` `(?:-->|\Z)`; `:803` `assertEqual(visible("shown\n<!-- swallowed\nalso swallowed"), "shown\n")`. `M9`, `M10`, `F14` killed.
- [x] **Command in a comment *and* in a live fenced block ⇒ pass** - `:468` `assertIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`. `M10`, `M16`, `R4` killed.
- [x] **No fenced block at all ⇒ fail, not raise** - `:946-963` returns `""`; `:718` `assertEqual(fenced_commands("## s\n\njust prose, no block\n").strip(), "")`; end-to-end via `A10`. ⚠️ same scope-vs-path naming caveat as AC 2.
- [x] **Negated fence + a second affirmative instance ⇒ pass** - `:556-565`, `:565` `assertIsNone(negated_by(rescued, self.COMMAND))`. `M6` (drop the affirmative short-circuit), `M2b`, `M20`, `F10` all kill it.
- [x] **Vocabulary matches no fence in any shipped document, asserted by a test** - `:677-698`, now through the production helpers. **Round-2 Gap B closed**: `V1` and `M2` both fail it. Re-derived independently: 0 offenders at `INTRO_LINES=4`.
- [x] **Prose must not rescue a negated fence** - `:670-675`; `:655-662` through `assert_instructs`. `N7` → guard killed; `M8` kills `:655`.
- [x] **A negation up to `INTRO_LINES` lines above the fence is still read** - `:585-598`. `M1` (4→3) and `F2` kill it. Ceiling now supplied by the corpus net (`M2c` at width 8).
- [x] **Inline mention reads the text before the command on its line** - `:625-629`, `:631-633`. ⚠️ "before" is still unpinned (`M21`, `D1` survive) - Gap D.
- [x] **Unterminated fence runs to the end** (new, `spec.md:38` records the `_fenced()` half as deliberately unfixed) - `:646-653`. `M13` kills it.

---

### Discrimination Sensor

**Isolation**: one detached `git worktree add --detach` at `9a6a9ba`, removed
with `git worktree remove --force`. Real tree `git status --porcelain` **empty
before and empty after**; `git worktree list` shows only the primary tree; `git
stash list` empty, no `git stash` used. Sensor run is valid.

**Methodology - stale bytecode.** `scripts/__pycache__` is deleted before
**every** run (`sensor.run()`), per the round-2 finding: CPython invalidates a
`.pyc` on `(mtime, size)`, so a same-length mutation landing in the same mtime
second is silently ignored, and the failure is one-directional - mutants look
*covered* when they are not. The purge stays mandatory.

**Scope note**: mutations are scored against `test_unit_docs_parity.py` alone;
no other module imports it. Document mutations are scored at **guard level** -
the named guard failing, not merely the suite going red.

#### Original probes

| # | Mutation | Expect | Result | Guard failed? |
| - | -------- | ------ | ------ | ------------- |
| P1 | Phase H intro → `"Never run this, it is not a supported operation:"` | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P1b | Phase H intro → `"A human deletes \`loop.json\` and starts over. Whatever you do, never run:"` | kill | ✅ Killed | **YES** - same guard |
| P2 | `` ## `halt` `` block wrapped in an HTML comment | kill | ✅ Killed | **YES** - `test_the_halt_field_section_names_the_command` |
| P7 | column-0 `# resolve the cause first` inside the Phase H fence | **survive** | ✅ Survived | n/a - correct, no false positive |

#### Document attacks

| # | Mutation | Expect | Result | Guard failed? |
| - | -------- | ------ | ------ | ------------- |
| P2b | Phase H bash block wrapped in an HTML comment | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P2c | `H` row's `` `update_loop.py --resume` `` wrapped in an HTML comment | kill | ✅ Killed | **YES** - `test_the_transition_row_names_the_command` |
| P2d | Phase B `--gate-attempt` block wrapped in an HTML comment | kill | ✅ Killed | **YES** - `test_the_call_sits_in_the_phase_that_runs_the_gate` |
| N5 | Phase H rewritten as a **one-line** command under `"Never run this:"` | kill | ✅ Killed | **YES** |
| N6 | `H` row → `"Whatever you do, never run \`update_loop.py --resume\`."` | kill | ✅ Killed | **YES** |
| N7 | affirmative prose mention added, fence negated | kill | ✅ Killed | **YES** |
| N8 | `state-schema.md` → `"It was cleared by one command. Do not run:"` | kill | ✅ Killed | **YES** |
| A10 | whole Phase H block moved into prose | kill | ✅ Killed | **YES** |
| G4 | Phase B timeout intro genuinely negated (`"Never run this, it corrupts the state file:"`) | kill | ✅ Killed | **YES** - `test_a_nearby_negation_about_something_else_does_not_flag` **+** the AC-6 net. Gap A's repaired test is load-bearing |
| N9 | `# never run the destructive variant; run this instead` **inside** the Phase H fence | **survive** | ✅ **Survived** | n/a - **round-2 false positive fixed**: the net reads fence *openings* now, not every fence line |
| D1 | `H` row negation placed **after** the command | kill | Survived | n/a - out of scope by design (`spec.md:116` says *preceding*); Gap D |
| N4 | negation outside the vocabulary (`"This call was removed in 0.4 and will error:"`) | kill | ⚠️ Guard green | NO - recorded residual risk, `spec.md:50`, `:496-499` |
| N2 | command split across two abutting fences | kill | ❌ Survived (guard green) | NO - **round-1 Gap 7** still latent; 0 shipped adjacent fence pairs |
| N3 | `<!--` inside the Phase H bash block | **survive** | ❌ Killed | **YES** - **round-1 Gap 8** still latent; 0 shipped occurrences, **now recorded** `spec.md:39` |
| A2 | Phase H fence opened, closing `` ``` `` deleted | kill | ⚠️ Guard green | NO - **round-1 Gap 6** still latent; 0 shipped odd fence counts, **now recorded** `spec.md:38` |
| V1 | `"commit"` added to `IMPERATIVE_VERBS` + `SPELLED_OUT` | AC-6 net fires | ✅ **Net fires** | **YES** - `test_the_vocabulary_flags_no_fence_in_any_shipped_document`. **Round-2 Gap B closed** (round 2: net silent) |

#### Helper and constant mutations

| # | Mutation | Result | Killed by |
| - | -------- | ------ | --------- |
| M1 | `INTRO_LINES` 4 → 3 | ✅ Killed | `test_a_negation_wrapped_over_several_lines_is_still_read` |
| M2 | `INTRO_LINES` 4 → **10** | ✅ **Killed** | `test_the_vocabulary_flags_no_fence_in_any_shipped_document` - **round-2 Gap E closed** |
| M2b | `INTRO_LINES` 4 → 40 | ✅ Killed | the net + `test_an_affirmative_copy_rescues_a_negated_one` |
| M2c | `INTRO_LINES` 4 → 8 | ✅ Killed | the net (first corpus offender is at width 8) |
| M2d | `INTRO_LINES` 4 → 5 | ❌ Survived | — corpus cannot separate 4 from 5-6; measured, not assumed |
| M3 | `IMPERATIVE_VERBS` → `("run",)` | ✅ Killed | `test_every_spelled_out_marker_is_detected` + the agreement check |
| M4 | `NEGATED_IMPERATIVES = ()` | ✅ Killed | 11 tests |
| M5 | `negated_by()` → always `None` | ✅ Killed | 10 tests |
| M6 | `negated_by()` ignores the affirmative short-circuit | ✅ Killed | `test_an_affirmative_copy_rescues_a_negated_one` |
| M7 | `assert_instructs` forces `fenced=True` | ✅ Killed | `test_the_guard_itself_rejects_a_negated_inline_row` |
| M8 | `assert_instructs` forces `fenced=False` | ✅ Killed | `test_the_guard_itself_rejects_a_negated_fence` |
| M9 | `visible()` → `return text` | ✅ Killed | 5 tests |
| M10 | `visible()` → `return ""` | ✅ Killed | 20 tests, incl. **all four guards** |
| M11 | `section()` → `fenced = set()` | ✅ Killed | 3 tests |
| M12 | `fenced_commands()` → `return text` | ✅ Killed | 3 tests |
| M13 | `fence_spans()` drops the unterminated branch | ✅ **Killed** | `test_an_unterminated_fence_runs_to_the_end` - **round-2 Gap F closed** |
| M14 | `table_row()` takes the first match | ✅ Killed | `test_each_scope_excludes_the_passage_that_follows_it` |
| M15 | `_fenced()` → `return set()` | ✅ Killed | 11 tests, incl. 3 guards |
| M16 | `collapsed()` → `return text` | ✅ Killed | 9 tests, incl. 2 guards |
| M19 | restore the **pre-fix** (`a82c10e`) `negated_by` verbatim | ✅ Killed | 8 tests - AC 5 non-vacuous |
| M20 | fenced intro window starts at line 0 | ✅ Killed | the net + `test_an_affirmative_copy_rescues_a_negated_one` |
| M21 | inline intro `(line.split(command,1)[0], line)` → `(line, line)` | ❌ Survived | — Gap D |
| M22 | inline branch drops the `number not in inside` fence exclusion | ❌ Survived | — Gap G |
| M23 | `assert_instructs` haystack → `collapsed(scope)` | ❌ Survived | — Gap C |
| M24 | *control*: `INTRO_LINES`=10 **and** the AC-6 net re-decoupled | Survives (correct) | — proves the coupling is what kills `M2` |

#### Fresh attacks on `fence_intro()` and the last commit

| # | Mutation | Result | Killed by |
| - | -------- | ------ | --------- |
| F1 | `fence_intro()` → `""` | ✅ Killed | 9 tests |
| F2 | `fence_intro()` window narrowed by one line | ✅ Killed | `test_a_negation_wrapped_over_several_lines_is_still_read` |
| F3 | `fence_intro()` also includes the fence opener line | ❌ Survived | — equivalent on this corpus: a `` ```lang `` line can hold no marker |
| F4 | `fence_intro()` reads the lines **below** the opener | ✅ Killed | 9 tests |
| F5 | `fence_spans()` closing index +1 | ❌ Survived | — inert: the extra line is the closing `` ``` `` and never removes a command from the body |
| F6 | `fence_spans()` treats **every** fence line as an opening (the old net's bug, moved into production) | ✅ Killed | 8 tests |
| F7 | *control*: AC-6 net re-decoupled (hardcoded `4` + clause split restored) | Survives (correct) | — identical output at `INTRO_LINES=4`; only `M24` separates them |
| F8 | *control*: AC-6 net never appends an offender | Survives (circular) | — a test cannot test itself; the meaningful proof is `V1`/`M2` |
| F9 | `fence_intro()` hardcodes `4` instead of `INTRO_LINES` | ❌ Survived | — literally equivalent at the shipped value |
| F10 | `negated_by()` defaults to a marker when none matches ("always flag") | ✅ Killed | 9 tests, incl. all four guards |
| F11 | `assert_instructs` haystack always fenced (inline exemption removed) | ✅ Killed | `test_the_guard_itself_accepts_an_affirmative_inline_row`, `test_the_transition_row_names_the_command` |
| F12 | `section()` `depth <= level` → `depth < level` | ✅ Killed | `test_the_section_still_ends_at_the_real_heading` + 2 |
| F13 | `section()` inverts the post-`#` space check | ✅ Killed | same + `test_a_shell_comment_in_phase_h_leaves_the_guard_passing` |
| F14 | `visible()` loses `re.DOTALL` | ✅ Killed | 4 tests |
| F16 | the corpus iterator yields no document | ✅ Killed | `test_a_bare_negation_list_would_flag_shipped_prose` - the AC-6 net's positive control |
| G1 | `"retry"` added to `IMPERATIVE_VERBS` | ✅ Killed | `test_a_nearby_negation_about_something_else_does_not_flag` - **round-2 Gap A closed** |
| G2 | `NEGATED_IMPERATIVES = ()` scored against the Gap-A test | Correctly green | — emptying the vocabulary can only remove flags; a negative assertion must not be sensitive to it |
| G3 | `INTRO_LINES` → 20 scored against the Gap-A test | Correctly green | — and the comment at `:536-543` no longer claims width is what keeps it affirmative |

#### Pre-existing guards (regression)

| # | Mutation | Result | Killed by |
| - | -------- | ------ | --------- |
| R1 | drop `blast_radius` from the SKILL.md halt-reason list | ✅ Killed | `test_skill_md_enumerates_exactly_the_implemented_reasons` |
| R2 | reintroduce `"disposable"` in `state-schema.md` | ✅ Killed | `test_no_shipped_document_repeats_a_retracted_claim` |
| R4 | rename the `` ## `halt` `` heading | ✅ Killed | `test_the_halt_field_section_names_the_command` + 3 |
| R6 | reintroduce `` clearing `halt.reason` `` in the `H` row | ✅ Killed | `test_no_shipped_document_sends_the_reader_to_the_field` |
| R8 | remove `--gate-attempt` from Phase B | ✅ Killed | `test_skill_md_names_the_call_that_records_a_failed_gate` + 1 |

**No pre-existing parity check was weakened: 5/5 regression mutants killed**
(round 1: 8/8, round 2: 5/5).

**Sensor depth**: P0-full, **68 mutations**
**Outcome**: 55 killed, 13 survived. Of the survivors, **3 are correct**
(`P7`, `N9`, `D1` - false-positive and out-of-scope probes that must not fire),
**6 are equivalent or circular** (`F3`, `F5`, `F7`, `F8`, `F9`, `M24`), and
**4 are genuine unexpected survivors** (`M21`, `M22`, `M23`, `M2d`). Separately,
3 document attacks leave the guard green while the suite reddens (`N2`, `A2`,
`N4`) and 1 is a false positive (`N3`) - all four are round-1 latents at 0
shipped occurrences, and 3 of the 4 are now recorded in `spec.md` Out of Scope.

Round-over-round: round 1 had 4 unexpected + 6 partial of 32; round 2 had 6
survivors + 2 false positives + 1 silent net of 46; round 3 has **4 genuine
survivors and 1 false positive of 68**, none of them a wrong answer - each is an
unpinned branch or a corpus that cannot separate two values.

---

### Unfalsifiable-Test Hunt

This is the feature's recurring defect (three found across rounds 1-2, all in
test code), so round 3 hunted for it systematically rather than by reading.

**Method**: 34 tests were added on this branch and 0 removed
(`git show 700436c:scripts/test_unit_docs_parity.py` vs `HEAD`). The union of
tests failed by all 68 mutations was subtracted from the module's 69 tests.
27 came back never-killed; 24 of those are pre-existing checks this battery
never targeted (config parity, README enumerations, retracted-claim scans).
**Three of the 34 new tests were never killed**, and each was then attacked
directly:

| Test | Targeted mutation | Result |
| ---- | ----------------- | ------ |
| `test_an_affirmative_inline_mention_passes` `:631-633` | `F10` - `negated_by` defaults to a marker | ✅ Killed |
| `test_the_guard_itself_accepts_an_affirmative_inline_row` `:664-668` | `F11` - haystack always fenced | ✅ Killed |
| `test_the_section_still_ends_at_the_real_heading` `:763-766` | `F12`, `F13` - `section()` terminator relaxed | ✅ Killed |

**Outcome: 0 unfalsifiable tests remain among the 34 this feature added.** Round
1 found 2, round 2 found 1 carried; round 3 finds none.

Two written claims were also checked against the code rather than accepted:

- `:647-649` *"`_fenced()` already assumes this"* - verified: `_fenced()`'s
  `inside` flag never resets, so an unclosed fence does run to EOF. **True.**
- `:682` *"30 fence lines where only 15 open one"* - measured on SKILL.md:
  30 marker lines, 15 openings. **True.** (Corpus-wide: 162 and 81.)

---

### Gate Check

- **Gate command**: `rm -rf scripts/__pycache__ && python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Run 1**: **612 passed, 0 failed, 0 skipped** (134.7s), exit code 0
- **Run 2**: **612 passed, 0 failed, 0 skipped** (136.3s), exit code 0
- **Stability**: two independent runs, both with a purged `__pycache__`, identical results. No flake.
- **Count**: round 2 `3821649` = 611 total / 68 in the parity module; round 3 `9a6a9ba` = **612 total / 69**. **Delta +1** (`test_an_unterminated_fence_runs_to_the_end`); 1 test renamed and repaired, **0 deleted**.
- **Branch total**: `main` (`700436c`) 496 unit / 35 in the parity module → `HEAD` 69 in the parity module, **+34 tests, 0 removed**.

---

### Weakening Analysis (`3821649` → `9a6a9ba`)

Nothing is weaker. The commit is test-only and every change is neutral or
strengthening:

| Change | Direction |
| ------ | --------- |
| `fence_intro()` extracted `:895-904`; `negated_by` `:926` calls it | **Neutral in behaviour, strengthening in structure** - identical window; the duplicate definition it replaces is gone. `F9` proves the extraction is behaviour-preserving |
| AC-6 net `:688-692` rewritten onto `fence_spans()` + `fence_intro()` | **Strictly stronger** - was narrower than production (clause split, hardcoded 4) *and* wider in the wrong place (closing fences read as openings). `V1`, `M2` now fail it; `N9` no longer falsely fails it |
| `test_a_negation_in_an_earlier_sentence_does_not_flag` → `test_a_nearby_negation_about_something_else_does_not_flag` `:535-554` | **Strictly stronger** - was unfalsifiable; `G1`, `G4`, `F10` now kill it. Renaming is honest: the old name described a claim the spec retracted |
| `test_an_unterminated_fence_runs_to_the_end` `:646-653` added | **Stronger** - `M13` goes from survivor to killed |
| `spec.md` Out of Scope + 3 rows (`:38-40`) | Neutral (documentation) - records `_fenced()`'s unterminated rule, `visible()` inside fences, and the `INTRO_LINES` ceiling |

**Is the repaired Gap-A test a change-detector?** No. `:549-553` is a
precondition, not an assertion about the vocabulary: it fails loudly if the
shipped Phase B block ever stops matching the needle, which is precisely the
silent failure that let the old version assert nothing for a round. The
behavioural claim is `:554`, and `G1`/`G4` prove it discriminates.

**Newly added unfalsifiable tests**: none.
**Pre-existing unfalsifiable tests left in place**: none.

---

### Remaining Limits (accepted, recorded)

Each of these is behaviour that is **correct today** with a test-coverage or
exposure hole, not a wrong answer:

| Item | Kind | Exposure | Recorded? |
| ---- | ---- | -------- | --------- |
| `M23` - fence requirement unpinned through `assert_instructs` (Gap C) | test coverage | behaviour covered by `A10`, `:727-742`, `F11` | not in `spec.md`; one `assertRaises` fixes it |
| `M21`, `D1` - inline "preceding text" anchor unpinned (Gap D) | test coverage | `spec.md:116` scopes it to *preceding*; no shipped document has the shape | behaviour is as specified |
| `M22` - inline branch's fence exclusion unpinned (Gap G) | test coverage | no shipped inline guard has a fence in scope | cosmetic |
| `M2d` - corpus cannot separate `INTRO_LINES` 4 from 5-6 | measurement limit | floor 3 and ceiling 8 both pinned | `spec.md:40` |
| `N3` - `visible()` strips `<!--` inside a fence (round-1 Gap 8) | false positive | 0 shipped occurrences | ✅ `spec.md:39` |
| `A2` - `_fenced()` has no unterminated-fence rule (round-1 Gap 6) | latent | 0 shipped odd fence counts | ✅ `spec.md:38` |
| `N2` - `fenced_commands()` concatenates abutting fences (round-1 Gap 7) | latent | 0 shipped adjacent fence pairs | ❌ **not recorded** - the only round-1 latent with no Out-of-Scope row |
| `N4` - a negation outside the vocabulary still passes | residual risk | inherent to substring parity | ✅ `spec.md:50` and `:496-499` |
| AC 2/3 failure messages name the scope, not the document path | message precision | carried 3 rounds; `where` still identifies the passage | not recorded |

---

### Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ one extracted helper (`fence_intro`), no new machinery |
| Surgical changes | ✅ one source file touched; no shipped document changed |
| No scope creep | ✅ prose scans left alone per `spec.md:33` |
| Matches patterns | ✅ module-level helpers + docstring-as-rationale |
| Spec-anchored outcome check | ✅ AC 6's asserting test now exercises the guard |
| Per-layer Coverage Expectation | ⚠️ 3 unpinned branches remain (`M21`, `M22`, `M23`) |
| Every test maps to a spec requirement | ✅ the orphaned test was repaired and re-anchored to AC 6's vocabulary rationale |
| No unfalsifiable assertions | ✅ 0 of 34 added tests; hunted systematically, not by reading |
| Documented guidelines followed | ✅ none exist - strong defaults applied (`tasks.md:19`) |

---

### Requirement Traceability Update

| Requirement | Round-1 | Round-2 | Round-3 |
| ----------- | ------- | ------- | ------- |
| INTENT-01 (P1 AC 1, 2 - HTML comments) | ✅ Verified | ✅ Verified | ✅ **Verified** - all four guards now proven at guard level (`P2`, `P2b`, `P2c`, `P2d`) |
| INTENT-02 (P1 AC 3, 7 - fence required / inline exempt) | ❌ Needs Fix | ✅ Verified | ✅ **Verified** - AC 7 fully pinned (`F10`, `F11`); AC 3 correct with the `M23` coverage note |
| INTENT-03 (P1 AC 4, 5, 6 - negation vocabulary) | ❌ Needs Fix | ❌ Needs Fix | ✅ **Verified** - Gap B closed (`V1`, `M2` fail the net), Gap A closed (`G1`, `G4` kill the test), Gap F closed (`M13`) |
| INTENT-04 (P2 AC 1, 2, 3 - fence-aware section) | ✅ Verified | ✅ Verified | ✅ **Verified** - AC 2 now pinned directly (`F12`, `F13`) |

---

### Summary

**Overall**: ✅ PASS.

**Spec-anchored check**: 7/10 ✅ PASS, 3 ⚠️ precision, 0 ❌ GAP
**Sensor**: 68 mutations - 55 killed, 3 correct survivors, 6 equivalent/circular, **4 genuine survivors**, 1 false positive
**Gate**: 612 passed, exit 0, stable across two purged runs
**Unfalsifiable tests**: 0 of 34 added

**Merge recommendation**: **merge.** Both Major gaps are closed and each was
verified by reversing round 2's own demonstration, not by re-reading the diff -
`V1` now fails the AC-6 net by name, and `G1`/`G4` now fail the Gap-A test that
previously could not fail for any document, window width or vocabulary. The
feature's Success Criteria all hold: P1, P1b and P2 kill their guard at guard
level, P7 does not fire, the gate is green on unchanged shipped documents, and
the vocabulary is measured against the corpus by a test that actually runs the
scan.

**Nothing remaining blocks the merge.** The four genuine survivors are unpinned
branches with correct behaviour underneath (`M21`, `M22`, `M23`) or a property of
the corpus rather than of the check (`M2d`). The four latents (`N2`, `N3`, `A2`,
`N4`) are all at 0 shipped occurrences and three of the four are recorded in
`spec.md` Out of Scope.

**Optional follow-ups, none blocking** (in the order they are worth doing):

1. Gap C - one `assertRaises(AssertionError)` around `assert_instructs` on a
   prose-only scope kills `M23`.
2. Gap D - one affirmative row whose cell mentions a negation *after* the
   command kills `M21` and `D1`.
3. Add an Out-of-Scope row for round-1 Gap 7 (`fenced_commands()` concatenates
   abutting fences), the only latent still undocumented.
4. Gap G - cosmetic; `M22` needs a fixture with a fence inside an inline scope.

---

# Appendix: Round-2 Report (2026-08-11, `a82c10e..3821649`) - superseded

Preserved for history. Reproduced from `3821649` with mechanical edits only:
headings demoted one level, and the labels `## Validation:` / `**Result**:` /
`| Result |` renamed so `validate_state.py`'s verdict scraper reads the round-3
verdict above and not this superseded one. No finding text was altered.

### Round-2 verdict: FAIL

**Round 2, narrow.** Every behavioural gap round 1 raised is genuinely closed,
verified at *guard* level and not merely at suite level: probes P1, P1b, P2 kill
the guard they target, P7 no longer fires, and the three fixes for gaps 2, 3 and
5 each kill their guard under a fresh document attack. No pre-existing check was
weakened. The gate is green and stable.

The verdict is FAIL on **test integrity**, on two items, both in the file that
is itself the integrity mechanism:

1. The fix corrected the false justification in `spec.md` but left it **verbatim
   in the code**, attached to a test that this round proves is *unfalsifiable
   for any document, any window width and any vocabulary*. Round 1 named that
   exact test; the commit deleted the other test on that list and left this one.
2. The one test the spec commissions as the safety net for AC 6 does not run the
   code it is guarding. A realistic one-line vocabulary addition makes the
   production scan flag a shipped fence while that test reports zero.

Neither is a defect in the shipped documents or in guard behaviour today. Both
have precise, small fixes, and one of them (`M25`) is verified green already.

**Diff surface**: `git diff a82c10e..3821649 --name-only` = `.specs/LESSONS.md`,
`.specs/features/parity-intent/spec.md`, `.specs/features/parity-intent/validation.md`,
`.specs/lessons.json`, `scripts/test_unit_docs_parity.py`. **No shipped document
changed.** Real tree `git status --porcelain` empty before and after the sensor;
no `git stash` used.

---

### Round 1 Gap Disposition

| Gap | Round-1 finding | Round-2 status | Evidence |
| --- | --------------- | -------------- | -------- |
| 1 (Major) | AC 5 vacuous, justification false | ⚠️ **Half-fixed** | Spec corrected (`spec.md:48`, `spec.md:73`); clause split removed; AC 5 now discriminating (sensor `M19` restores the pre-fix `negated_by` and kills 7 tests). **But** `scripts/test_unit_docs_parity.py:535-545` survives untouched, still unfalsifiable and still carrying the retracted claim - see New Gap A |
| 2 (Major) | AC 4 fails for a one-line command | ✅ **Fixed** | `fence_spans()` `:854-871` + `INTRO_LINES` `:851`; `negated_by` `:892-896` anchors on `opening`. Sensor `N5` (Phase H rewritten to a one-line command under `Never run this:`) → **guard killed** |
| 3 (Major) | AC 7 inline negation inert | ✅ **Fixed** | `negated_by(..., fenced=False)` inline branch `:898-903`; `assert_instructs` threads it `:383`. Sensor `N6` (negated `H` row in the shipped file) → **`test_the_transition_row_names_the_command` killed** |
| 4 (Minor) | P7 replay used an indented `#` | ✅ **Fixed** | `:756` now injects at column 0. Sensor `P7` survives (correct); `M11`/`M15` kill it |
| 5 (Minor) | Prose rescues a negated fence | ✅ **Fixed** | `fenced` threaded into `negated_by` `:383`. Sensor `N7` (affirmative prose mention + negated fence, in the shipped SKILL.md) → **guard killed**; `M8` kills `test_the_guard_itself_rejects_a_negated_fence` |
| 6 (Minor) | `_fenced()` unterminated-fence rule | ➖ **Not fixed, latent** | 0 shipped docs have an odd ``` ``` ``` count. Behaviour is in fact correct (`inside` never resets, so an unclosed fence runs to EOF), but nothing pins it: `M13` (delete `fence_spans`' unterminated branch `:869-870`) **survived**, so the docstring claim at `:857-859` is unfalsifiable. Sensor `A2` still only catches it incidentally (guard green). **Defensible to defer**; the docstring should not claim what no test holds |
| 7 (Cosmetic) | `fenced_commands()` concatenates fences | ➖ **Not fixed, latent** | 0 shipped adjacent fence pairs. Sensor `N2` (command split across two abutting fences) → **guard green**. Defensible: requires a contrived document |
| 8 (Minor) | `visible()` strips `<!--` inside fences | ➖ **Not fixed, latent** | 0 shipped `<!--` lines inside a fence. Sensor `N3` (a `<!--` in the Phase H bash block) → **guard killed on a valid document** - the false-positive class P7 exists to remove. Defensible to defer on exposure, **not** defensible to leave unrecorded: `spec.md` has no Out-of-Scope row or edge case for it |

---

### Spec-Anchored Acceptance Criteria

All `file:line` refer to `scripts/test_unit_docs_parity.py` at `3821649` unless stated.

#### P1: A guard rejects a document that does not instruct

| Criterion | Spec-defined outcome | `file:line` + assertion | Outcome |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - ignore every `<!-- ... -->` span, incl. multi-line | every span removed | impl `:302` `re.sub(r"<!--.*?(?:-->\|\Z)", "", text, flags=re.DOTALL)`; `:774` `assertEqual(visible("keep <!-- drop --> keep"), "keep  keep")`; `:777` `assertEqual(visible("a\n<!-- one\ntwo\nthree -->\nb"), "a\n\nb")`; `:794` `assertNotIn("<!--", stripped)`. Sensor `M9` (no-op) killed 5 tests, `M10` (strip-all) killed 20 incl. all four guards | ✅ PASS |
| AC 2 - command only inside a comment ⇒ guard fails, naming the document | fail + document named | `:459` `assertNotIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`; guard `:435-442`. Sensor `P2` → `test_the_halt_field_section_names_the_command` killed | ⚠️ Precision (carried) - fails correctly; the message names the **scope** (`"the \`halt\` field section"`, `:441`), not the document path |
| AC 3 - fenced-artifact guard fails when the command is prose-only | fail + document named | impl `:376` `haystack = collapsed(fenced_commands(scope) if fenced else scope)`; `:691` `assertNotIn("thing --flag", fenced_commands(self.DOC))`; `:718-721` `assertNotIn(cmd, collapsed(fenced_commands(rescoped)))`. Sensor `A10` (whole Phase H block de-fenced) → **guard killed** | ⚠️ Precision - behaviour correct, but the requirement is **not pinned through `assert_instructs`**: sensor `M23` (`haystack = collapsed(scope)`) **survived the whole suite**. See New Gap C |
| AC 4 - negated introducing clause ⇒ guard fails, naming the marker | fail + marker named | impl `:383-388`; `:522` `assertEqual(negated_by(body, self.COMMAND), "never run")`; `:533` same for P1b; `:614` one-line variant; `:589` wrapped variant. Sensors `P1`, `P1b`, `N5`, `N7`, `N8` → **guard killed** in every case; `M4`/`M5` kill 9-10 tests | ✅ PASS - round-1 Gap 2 closed |
| AC 5 - anchor the lookbehind to the command's own fence opener, or to the text preceding it on its line | anchored, not scan-relative | impl `:874-911`; fenced anchor `:892-896`; inline anchor `:900` `(line.split(command, 1)[0], line)`; `:614` `assertEqual(negated_by("## s\n\ntext\n\nNever run this:\n\`\`\`bash\nthing --flag\n\`\`\`\n", "thing --flag"), "never run")`; `:620` inline row. **Non-vacuity proof**: sensor `M19` restores the pre-fix scan-anchored `negated_by` verbatim → kills 7 tests including `:609` and `:616`; `M1` (`INTRO_LINES` 4→3) kills `:576`; `M20` (window start → line 0) killed | ⚠️ Precision - the *fenced* half is genuinely discriminating (round-1 Gap 1 closed for the criterion). The *inline* half's "text **preceding** it" is unpinned: sensor `M21` (`(line, line)`) **survived**. See New Gap D |
| AC 6 - vocabulary verb-specific **and** flags no shipped fence | 0 offenders; verb-specific only | verb-specific: `:561-565` `SPELLED_OUT` written out + `:574` `assertEqual(sorted(self.SPELLED_OUT), sorted(NEGATED_IMPERATIVES))` + `:570` `assertEqual(negated_by(doc, "thing --flag"), marker, marker)` for all 15. Sensor `M3` (`IMPERATIVE_VERBS = ("run",)`) kills **both** → round-1 Gap 8 (tautology) closed. flags-none: `:672` `assertEqual(offenders, [], ...)`; independently re-derived with production semantics at `INTRO_LINES=4` → **0 offenders** | ❌ **GAP** - criterion holds today, but the test asserting it runs a different algorithm than the guard. See New Gap B |
| AC 7 - inline guard applies criteria 1, 2, 4; does not require a fence | negation rejected on the inline mention | `:427` `read_visible(...)` (crit 1-2); `:432` `fenced=False` (no fence required); `:620` `assertEqual(negated_by(row, "update_loop.py --resume", fenced=False), "never run")`; `:626-635` `with self.assertRaises(AssertionError): assert_instructs(..., fenced=False)`; `:646-650` affirmative row accepted. Sensor `N6` → **guard killed**; `M7` (force `fenced=True`) killed `:626` | ✅ PASS - round-1 Gap 3 closed |

#### P2: A fenced `#` does not truncate a scope

| Criterion | Spec-defined outcome | `file:line` + assertion | Outcome |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - section scan ignores lines inside fences | fenced lines skipped when locating the terminator | impl `:818-821` `fenced = _fenced(lines)` / `if number in fenced: continue`; `:740` `assertIn("more first-section text", body)`. Sensor `M11` (`fenced = set()`) killed 3 tests | ✅ PASS |
| AC 2 - section still extends to the next real heading | reaches the next real heading, stops there | `:743-744` `assertNotIn("## second", body)` / `assertNotIn("other", body)`; `:748` `assertIn("# not a heading", section(...))`. Sensors `M11`, `M15` killed | ✅ PASS |
| AC 3 - guards inside such a section still pass on the shipped documents | Phase H guard passes, scope still ends at `### Step 3` | `:756` now injects `"# resolve the cause first\n"` at **column 0**; `:763-766` `assertIn(cmd, collapsed(fenced_commands(body)))`; `:767` `assertNotIn("### Step 3", body)`. Sensor `P7` (column-0 `#` in the shipped file) survives correctly; `M11`/`M15` kill this test | ✅ PASS - round-1 Gap 4 closed |

**Status**: 4 ✅ PASS, 3 ⚠️ precision, 1 ❌ GAP across 10 criteria (round 1: 3 / 4 / 3).

---

### Edge Cases

- [x] **Unterminated `<!--` hides the remainder** - `:302` `(?:-->|\Z)`; `:782` `assertEqual(visible("shown\n<!-- swallowed\nalso swallowed"), "shown\n")`. `M9`/`M10` killed.
- [x] **Command in a comment *and* in a live fenced block ⇒ pass** - `:468` `assertIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`. `M10`, `M16` killed.
- [x] **No fenced block at all ⇒ fail, not raise** - `:914-931` returns `""`; `:697` `assertEqual(fenced_commands("## s\n\njust prose, no block\n").strip(), "")`; end-to-end via sensor `A10`. ⚠️ same scope-vs-path naming caveat as AC 2.
- [x] **Negated fence + a second affirmative instance ⇒ pass** - `:547-556`, `:556` `assertIsNone(negated_by(rescued, self.COMMAND))`. Sensor `M6` (drop the affirmative short-circuit) killed it; `M2b`, `M20`, `A2` also kill it.
- [ ] **Vocabulary matches no fence in any shipped document, asserted by a test** - `:659-677`. The *fact* is true (re-derived independently: 0 offenders). The *test* does not assert it through the production path - **New Gap B**.
- [x] **Prose must not rescue a negated fence** (new) - `:652-657` `assertEqual(negated_by(doc, "thing --flag"), "never run")`; `:637-644` through `assert_instructs`. Sensor `N7` → guard killed; `M8` killed `:637`.
- [x] **A negation up to `INTRO_LINES` lines above the fence is still read** (new) - `:576-589`, marker sits exactly `INTRO_LINES` above. Sensor `M1` (4→3) kills it. ⚠️ lower bound only - `M2` (4→10) **survived**; see New Gap E.
- [x] **Inline mention reads the text before the command on its line** (new) - `:616-620`, `:622-624`. ⚠️ "before" is unpinned - `M21` survived; see New Gap D.

---

### Discrimination Sensor

**Isolation**: two detached `git worktree add --detach` trees at `3821649`, both
removed with `git worktree remove --force`. `git worktree list` shows only the
primary tree. Real tree `git status --porcelain` **empty before and empty
after**; `git stash list` empty. No `git stash` used. Sensor run is valid.

**Methodology - stale bytecode.** `scripts/__pycache__` is deleted before
**every** run (`sensor.py:run()`). The hazard was reproduced deliberately rather
than assumed: CPython invalidates a `.pyc` on `(mtime, size)`, so a mutation
that keeps the byte length **and** lands in the same mtime second is silently
ignored. Forcing `os.utime` back to the original mtime after writing
`INTRO_LINES = 2` (same length as `INTRO_LINES = 4`) produced `OK` without a
purge and `FAILED (failures=1)` with one. Under ordinary timing the interpreter
does invalidate correctly - but the failure mode is real, silent, and
one-directional (mutants look *covered* when they are not), so the purge stays
mandatory. The author's round-1 observation is confirmed.

**Scope note**: helper mutations were scored against `test_unit_docs_parity.py`
alone; no other module imports it (verified). Document mutations are scored at
**guard level** - the named guard failing, not merely the suite going red.

#### Original probes

| # | Mutation | Expect | Outcome | Guard failed? |
| - | -------- | ------ | ------ | ------------- |
| P1 | Phase H intro → `"Never run this, it is not a supported operation:"` | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P1b | Phase H intro → `"A human deletes \`loop.json\` and starts over. Whatever you do, never run:"` | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P2 | `` ## `halt` `` block wrapped in an HTML comment | kill | ✅ Killed | **YES** - `test_the_halt_field_section_names_the_command` |
| P7 | column-0 `# resolve the cause first` inside the Phase H fence | **survive** | ✅ Survived | n/a - correct, no false positive |

#### Document attacks on the new helpers

| # | Mutation | Expect | Outcome | Guard failed? |
| - | -------- | ------ | ------ | ------------- |
| N1 | Phase H fence `` ``` `` → `~~~` (valid CommonMark) | kill | ✅ Killed | YES - false-positive direction; repo uses `` ``` `` exclusively |
| N2 | command split across two abutting fences | kill | ❌ **Survived** | NO - **Gap 7** still latent (0 shipped adjacent fence pairs) |
| N3 | `<!--` inside the Phase H bash block | **survive** | ❌ **Killed** | **YES** - **Gap 8** still latent (0 shipped occurrences) |
| N4 | negation outside the vocabulary (`"This call was removed in 0.4 and will error:"`) | kill | ⚠️ Guard green | NO - recorded residual risk, `spec.md:47`, `:496-500` |
| N5 | Phase H rewritten as a **one-line** command under `"Never run this:"` | kill | ✅ Killed | **YES** - round-1 Gap 2 closed |
| N6 | `H` transition row → `"Whatever you do, never run \`update_loop.py --resume\`."` | kill | ✅ Killed | **YES** - round-1 Gap 3 closed |
| N7 | affirmative prose mention added, fence negated | kill | ✅ Killed | **YES** - round-1 Gap 5 closed |
| N8 | `state-schema.md` → `"It was cleared by one command. Do not run:"` | kill | ✅ Killed | **YES** - `test_the_halt_field_section_names_the_command` |
| N9 | `# never run the destructive variant; run this instead` **inside** the Phase H fence | **survive** | ❌ **Killed** | NO (guard green) - killed by `test_the_vocabulary_flags_no_fence_in_any_shipped_document`, which reads fence **bodies** as intros. New Gap B |
| N10 | `H` row negation placed **after** the command | kill | Survived | n/a - out of scope by design (`spec.md:113` says *preceding*) |
| A10 | whole Phase H block moved into prose | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| A2 | Phase H fence opened, closing `` ``` `` deleted | kill | ⚠️ Guard green | NO - **Gap 6** still latent (0 shipped odd fence counts) |
| V1 | `"commit"` added to `IMPERATIVE_VERBS` + `SPELLED_OUT` (a realistic vocabulary growth) | AC-6 net fires | ❌ **Net silent** | Suite red via `test_the_call_sits_in_the_phase_that_runs_the_gate` (coincidence - the fence is inside a guarded scope). The AC-6 net stayed green while production flagged `SKILL.md:250 ('do not commit')`. New Gap B |

#### Helper and constant mutations

| # | Mutation | Outcome | Killed by |
| - | -------- | ------ | --------- |
| M1 | `INTRO_LINES` 4 → 3 | ✅ Killed | `test_a_negation_wrapped_over_several_lines_is_still_read` |
| M2 | `INTRO_LINES` 4 → **10** | ❌ **Survived** | — **New Gap E** |
| M2b | `INTRO_LINES` 4 → 40 | ✅ Killed | `test_an_affirmative_copy_rescues_a_negated_one` (incidental) |
| M3 | `IMPERATIVE_VERBS` → `("run",)` | ✅ Killed | `test_every_spelled_out_marker_is_detected`, `test_the_spelled_out_list_and_the_vocabulary_agree` - **round-1 H10 closed** |
| M4 | `NEGATED_IMPERATIVES = ()` | ✅ Killed | 10 tests |
| M5 | `negated_by()` → always `None` | ✅ Killed | 9 tests |
| M6 | `negated_by()` ignores the affirmative short-circuit | ✅ Killed | `test_an_affirmative_copy_rescues_a_negated_one` |
| M7 | `assert_instructs` forces `fenced=True` in the negation call | ✅ Killed | `test_the_guard_itself_rejects_a_negated_inline_row` |
| M8 | `assert_instructs` forces `fenced=False` in the negation call | ✅ Killed | `test_the_guard_itself_rejects_a_negated_fence` |
| M9 | `visible()` → `return text` | ✅ Killed | 5 tests |
| M10 | `visible()` → `return ""` | ✅ Killed | 20 tests, incl. **all four guards** |
| M11 | `section()` → `fenced = set()` | ✅ Killed | `test_a_fenced_hash_does_not_end_the_section`, `test_the_fenced_line_is_still_part_of_the_section`, `test_a_shell_comment_in_phase_h_leaves_the_guard_passing` |
| M12 | `fenced_commands()` → `return text` | ✅ Killed | `test_a_scope_with_no_fence_yields_nothing`, `test_prose_outside_a_fence_is_not_an_instruction`, `test_moving_the_command_into_prose_fails_the_guard` |
| M13 | `fence_spans()` drops the unterminated branch (`:869-870`) | ❌ **Survived** | — **New Gap F** |
| M14 | `table_row()` takes the first match (`len(rows) != 1` → `< 1`) | ✅ Killed | `test_each_scope_excludes_the_passage_that_follows_it` (decoy row, `:483-486`) |
| M15 | `_fenced()` → `return set()` | ✅ Killed | 10 tests, incl. 3 guards |
| M16 | `collapsed()` → `return text` | ✅ Killed | 8 tests, incl. 2 guards |
| M19 | restore the **pre-fix** `negated_by` (scan-anchored + clause split) | ✅ Killed | 7 tests incl. `test_a_negation_directly_above_a_one_line_command_is_caught`, `test_a_negated_inline_mention_is_caught`, `test_prose_cannot_rescue_a_negated_fence` - **AC 5 is non-vacuous** |
| M20 | fenced intro window starts at line 0 instead of `opening - INTRO_LINES` | ✅ Killed | `test_an_affirmative_copy_rescues_a_negated_one` |
| M21 | inline intro `(line.split(command,1)[0], line)` → `(line, line)` | ❌ **Survived** | — **New Gap D** |
| M22 | inline branch drops the `number not in inside` fence exclusion | ❌ **Survived** | — **New Gap G** |
| M23 | `assert_instructs` haystack → `collapsed(scope)` (fence requirement removed) | ❌ **Survived** | — **New Gap C** |
| M24 | *diagnostic*: `INTRO_LINES`=10 **and** the AC-6 test re-coupled to production semantics | ✅ Killed | `test_the_vocabulary_flags_no_fence_in_any_shipped_document` - proves the decoupling is what let `M2` live |
| M25 | *diagnostic*: AC-6 test re-coupled to production semantics alone | Survives (correct) | — the fix for New Gap B is green today, no document change needed |

#### Pre-existing guards (regression)

| # | Mutation | Outcome | Killed by |
| - | -------- | ------ | --------- |
| R1 | drop `blast_radius` from the SKILL.md halt-reason list | ✅ Killed | `test_skill_md_enumerates_exactly_the_implemented_reasons` |
| R2 | reintroduce `"disposable"` in `state-schema.md` | ✅ Killed | `test_no_shipped_document_repeats_a_retracted_claim` |
| R4 | rename the `` ## `halt` `` heading | ✅ Killed | `test_the_halt_field_section_names_the_command` + 3 |
| R6 | reintroduce `` clearing `halt.reason` `` in the `H` row | ✅ Killed | `test_no_shipped_document_sends_the_reader_to_the_field`, `test_the_transition_row_names_the_command` |
| R8 | remove `--gate-attempt` from Phase B | ✅ Killed | `test_skill_md_names_the_call_that_records_a_failed_gate`, `test_the_call_sits_in_the_phase_that_runs_the_gate` |

**No pre-existing parity check was weakened: 5/5 regression mutants killed** (round 1: 8/8).

**Sensor depth**: P0-full, **46 mutations**
**Outcome**: 35 as expected; **6 survived when they should have been killed**
(`N2`, `M2`, `M13`, `M21`, `M22`, `M23`); **2 false positives** (`N3`, `N9`);
**2 guard-green latents** (`N4` recorded residual risk, `A2` Gap 6); **1 silent
safety net** (`V1`) - **FAIL (narrow)**

Round-1 comparison: 4 unexpected + 6 partial out of 32 → round 2 has zero
*behavioural* unexpected results on the fixed paths; every remaining survivor is
an untested branch or an unpinned constant, not a wrong answer.

---

### Gate Check

- **Gate command**: `rm -rf scripts/__pycache__ && python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Run 1**: **611 passed, 0 failed, 0 skipped** (141.5s)
- **Run 2**: **611 passed, 0 failed, 0 skipped** (143.4s), **exit code 0**
- **Stability**: two independent runs, both with a purged `__pycache__`, identical results. **No flake reproduced.** The round-1 flake is consistent with bytecode contamination, which the purge removes.
- **Count**: round 1 `a82c10e` = 601 total / 58 in the parity module; round 2 `3821649` = **611 total / 68 in the parity module**. **Delta +10** (11 added, 1 removed).
- **Tests deleted**: 1 - `test_the_vocabulary_is_verb_specific`, correctly replaced by `SPELLED_OUT` + `test_every_spelled_out_marker_is_detected` + `test_the_spelled_out_list_and_the_vocabulary_agree` (sensor `M3` proves the replacement discriminates where the original could not).

---

### Weakening Analysis (`a82c10e` → `3821649`)

Nothing is strictly weaker. Every change is neutral or strengthening:

| Change | Direction |
| ------ | --------- |
| `assert_instructs` `:383` `negated_by(scope, command)` → `negated_by(scope, command, fenced=fenced)` | **Stronger** - closes Gap 5 (`N7` kills the guard) and Gap 3 (`N6` kills the guard). `M7`/`M8` pin both directions |
| `negated_by` clause split (`rsplit(". ", 1)[-1]`) removed | **Stronger** - the window is now wider, so strictly more negations are seen. Re-derived: 0 new offenders on the shipped corpus at `INTRO_LINES=4` |
| `negated_by` anchored to `fence_spans()` instead of the scan index | **Stronger** - closes Gap 2 (`N5`); `M19` proves the difference is tested |
| `test_the_vocabulary_is_verb_specific` → `SPELLED_OUT` + 2 tests | **Stronger** - the old form was a tautology (`M3` survived in round 1, kills 2 tests now) |
| P7 replay `"   # ..."` → `"# ..."` | **Stronger** - now the probe it claims to be |
| 4 edge cases added to `spec.md:111-113` | Neutral (documentation), and each has a test |
| `spec.md:48` assumption row rewritten | **Correct** - retracts a false claim, explicitly labelled "Corrected after verification" |

**Is `SPELLED_OUT` + the agreement check a mere change-detector?** No. It is two
tests doing two jobs. `test_every_spelled_out_marker_is_detected` (`:567-570`)
drives all 15 markers end-to-end through `negated_by` against a real fixture -
that is behavioural coverage the old loop never had (round-1 `H10`: 12 of 15
markers unexercised). `test_the_spelled_out_list_and_the_vocabulary_agree`
(`:572-574`) is the change-detector half, and it is the right kind: it forces a
vocabulary edit to be restated in a form the comprehension cannot auto-satisfy.
`M3` kills both. Verdict: **pins the vocabulary, does not merely detect change.**

**Newly added unfalsifiable tests**: none. All 11 added tests are killed by at
least one mutation (`M3`, `M1`, `M4`, `M5`, `M7`, `M8`, `M19`).

**Pre-existing unfalsifiable test left in place**: one -
`test_a_negation_in_an_earlier_sentence_does_not_flag` (`:535-545`), New Gap A.

---

### New Gaps (round 2), ranked

#### New Gap A (Major) - an unfalsifiable test still carries the retracted claim

- **Location**: `scripts/test_unit_docs_parity.py:535-545`.
- **Unfalsifiable, proven**: the test passes the command **with its literal
  backslash-newline** - `"update_loop.py <feature> --root <root> \\\n     --halt executor"` -
  to `negated_by`, which only ever tests `command not in collapsed(body)`
  (`:905`). `collapsed()` (`:941`) flattens all whitespace, so no fence body can
  ever contain a string with an embedded newline. Measured: of the 6 fences in
  the Phase B scope, **0** match, the loop body never runs, and `negated_by`
  returns `None` unconditionally - at window widths 1, 2, 3, 4, 5, 6, 8, 10, 15,
  20 and 40, with the shipped vocabulary, with an **empty** vocabulary, and with
  a deliberately bare `("do not",)` vocabulary. Control: the same scope with the
  *collapsed* command form returns `"do not"` under `("do not",)` and
  `"never run"` when the intro is negated. The test asserts `assertIsNone` on a
  call that cannot return anything else.
- **Retracted claim, still shipped**: the comment at `:537-538` reads *"A
  window-based scan flags it; a clause-based one does not."* `spec.md:48` now
  states, in bold, that this is false and that no window could ever flag it, and
  there is no longer a clause-based scan to contrast with. This repo ships a
  `RETRACTED_CLAIMS` scanner over `scripts/*.py`; `SCANNER` (`:171`) exempts this
  one file from it, so nothing catches it.
- **Orphaned**: with AC 5 rewritten, this test traces to no acceptance criterion.
- **Fix**: delete the test and its comment, or repair it into a real probe -
  pass the collapsed command form and assert `None` against a fixture whose
  *earlier* sentence carries a genuine vocabulary marker. Round 1 raised this
  test by line number; it was the one item on that list left untouched.
- **Priority**: Major.

#### New Gap B (Major) - the AC-6 safety net does not test the guard it protects

- **Location**: `scripts/test_unit_docs_parity.py:659-677`.
- **Three ways it diverges from production** (`negated_by` `:874-911`):
  1. It still applies the clause split `intro.rsplit(". ", 1)[-1]` (`:668`) -
     the exact rule this commit removed from `negated_by`. It is therefore
     strictly **narrower** than the code it guards.
  2. It hardcodes `4` (`:667`) instead of `INTRO_LINES` (`:851`), so changing
     the constant is never re-measured against the corpus.
  3. It treats every ``` ``` ``` line as a fence intro. In the shipped corpus
     that is **162 lines, 81 of them closers**, so fence *bodies* are read as
     introducing prose.
- **Demonstrated failures**:
  - `M2`: `INTRO_LINES` 4 → 10 leaves the whole suite green while production
    flags a shipped fence (`SKILL.md:102`, marker `never pass`, first flagged at
    width 8). `M24` (re-couple + widen) kills; `M25` (re-couple alone) is green.
  - `V1`: adding `"commit"` to `IMPERATIVE_VERBS` - a plausible addition, the
    repo has a *"do not commit"* rule at `SKILL.md:246` - makes production read
    `SKILL.md:250` as a negated fence while this test reports **0 offenders**.
    The suite only went red by luck, via a different guard whose scope happens to
    contain that fence.
  - `N9`: a `# never run ...` shell comment inside a fence turns a valid
    document red **through this test**, the false-positive class the feature
    exists to remove.
- **Why it matters**: `spec.md:110` commissions this test verbatim *"so a later
  addition to the vocabulary cannot silently break valid prose"*. It cannot do
  that job while it scans different text than the guard.
- **Fix** (verified green as `M25`): replace `:666-668` with
  `for opening, _ in fence_spans(lines):` /
  `intro = " ".join(lines[max(0, opening - INTRO_LINES):opening]).lower()` and
  drop the `rsplit`. `test_a_bare_negation_list_would_flag_shipped_prose`
  (`:591-607`) already uses exactly that shape - the two scans in the same class
  disagree with each other.
- **Priority**: Major.

#### New Gap C (Minor) - the fence requirement is not pinned through `assert_instructs`

- `M23` (`:376` → `haystack = collapsed(scope)`) **survives the whole suite**.
  Behaviour is correct (`A10` kills the guard), but the only tests covering the
  fence requirement call `fenced_commands()` directly (`:691`, `:718-721`). The
  commit added `test_the_guard_itself_rejects_a_negated_fence` (`:637-644`) for
  the negation half of the same plumbing and left the presence half out.
- **Fix**: one test - `assert_instructs` on a scope whose command appears only in
  prose, wrapped in `assertRaises(AssertionError)`.
- **Priority**: Minor.

#### New Gap D (Minor) - the inline "preceding text" anchor is unpinned

- `M21` (`:900` `(line.split(command, 1)[0], line)` → `(line, line)`) **survives**.
  `spec.md:113` requires the negation be read from the text *before* the command
  on its line; no fixture places a marker after it (`N10` confirms the shape is
  otherwise undetected).
- **Fix**: one assertion - an affirmative row that mentions a negation later in
  the same cell must return `None`.
- **Priority**: Minor.

#### New Gap E (Minor) - `INTRO_LINES` has a floor but no ceiling

- `M1` (4→3) is killed by `:576-589`; `M2` (4→10) **survives**. Widening the
  window is the false-positive direction, and the corpus check that should bound
  it is Gap B. Fixing Gap B fixes this: under `M24`, widening to 10 is killed.
- **Priority**: Minor (subsumed by Gap B).

#### New Gap F (Minor) - `fence_spans()`' unterminated branch is unfalsifiable

- `M13` (delete `:869-870`) **survives**. The docstring at `:857-859` asserts
  *"An unterminated fence runs to the end"* and no test holds it. Same species as
  Gap A: a written claim with nothing behind it. Round-1 Gap 6 was deferred on
  exposure grounds (0 shipped odd fence counts, confirmed), which is defensible -
  but the untested claim is a one-line test away.
- **Priority**: Minor.

#### New Gap G (Cosmetic) - the inline branch's fence exclusion is unpinned

- `M22` (drop `number not in inside` at `:902`) **survives**. A fenced occurrence
  would count as an inline mention. No shipped inline guard has a fence in scope.
- **Priority**: Cosmetic.

---

### Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ one new helper (`fence_spans`) + one constant; `_fenced()` reused |
| Surgical changes | ✅ one source file touched; no shipped document changed |
| No scope creep | ✅ prose scans left alone per `spec.md:33` |
| Matches patterns | ✅ module-level helpers + docstring-as-rationale |
| Spec-anchored outcome check | ⚠️ AC 6's asserting test does not exercise the guard (Gap B) |
| Per-layer Coverage Expectation | ⚠️ 6 unpinned branches/constants (`M2`, `M13`, `M21`, `M22`, `M23`, `N2`) |
| Every test maps to a spec requirement | ❌ `:535-545` maps to no criterion since AC 5 was rewritten (Gap A) |
| No unfalsifiable assertions | ❌ one carried over (Gap A); **none newly introduced** |
| Documented guidelines followed | ✅ none exist - strong defaults applied (`tasks.md:19`) |

---

### Requirement Traceability Update

| Requirement | Round-1 Status | Round-2 Status |
| ----------- | -------------- | -------------- |
| INTENT-01 (P1 AC 1, 2 - HTML comments) | ✅ Verified | ✅ Verified |
| INTENT-02 (P1 AC 3, 7 - fence required / inline exempt) | ❌ Needs Fix (Gap 3) | ✅ Verified - AC 7 closed (`N6`); AC 3 correct, test-coverage note (Gap C) |
| INTENT-03 (P1 AC 4, 5, 6 - negation vocabulary) | ❌ Needs Fix (Gaps 1, 2) | ❌ **Needs Fix** - AC 4 and AC 5 closed (`N5`, `N6`, `N7`, `M19`); AC 6's safety net is Gap B, and Gap A sits in this requirement's test class |
| INTENT-04 (P2 AC 1, 2, 3 - fence-aware section) | ✅ Verified | ✅ Verified - Gap 4 closed, replay is now a true P7 |

---

### Summary

**Overall**: ⚠️ Issues - the behavioural work is done; two test-integrity items remain.

**Spec-anchored check**: 4/10 ✅ PASS, 3 ⚠️ precision, 1 ❌ GAP (was 3/4/3)
**Sensor**: 46 mutations - 35 as expected, 6 survivors, 2 false positives, 2 latents, 1 silent net
**Gate**: 611 passed, exit 0, stable across two purged runs

**What round 2 confirms works**:

- P1, P1b, P2 kill their guard; P7 does not fire. All four verified at guard level.
- Round-1 Gaps 2, 3, 4 and 5 are closed, each by a fresh document attack against
  the shipped corpus (`N5`, `N6`, `P7`, `N7`), not merely by the author's own probes.
- AC 5 is no longer vacuous: `M19` restores the pre-fix scan and kills 7 tests.
- The tautology is gone: `M3` now kills two tests where it survived in round 1.
- No pre-existing check weakened; nothing strictly weaker in the diff; +10 tests;
  the one deletion was the tautology and its replacement discriminates.
- Gaps 6, 7 and 8 confirmed latent at **0 shipped occurrences each**
  (odd fence counts: 0; `<!--` inside a fence: 0; adjacent fence pairs: 0).

**Issues found**: New Gaps A-G above. A and B are Major and both are the same
species this feature exists to eliminate - a claim in writing with no executable
check behind it. Gap B's fix is verified green today (`M25`).

**Next steps**: route New Gaps A and B to fix tasks; C, D, E, F, G are optional
hardening; record a decision for round-1 Gap 8 in `spec.md` Out of Scope rather
than leaving it undocumented. Re-verify after the fixes.

---

# Appendix: Round-1 Report (2026-08-11, `928f53e..a82c10e`) - superseded

Preserved for history. Reproduced from `a82c10e` with two mechanical edits only:
headings demoted one level, and the labels `## Validation:` / `**Result**:` /
`| Result |` renamed so `validate_state.py`'s verdict scraper reads the round-2
verdict above and not this superseded one. No finding text was altered.

**Date**: 2026-08-11
**Spec**: `.specs/features/parity-intent/spec.md`
**Diff range**: `main...HEAD` = `928f53e..a82c10e` (4 commits) on `fix/parity-guards-prove-intent`
**Verifier**: independent sub-agent (author ≠ verifier)

---

### Round-1 verdict: FAIL

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

### Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1 - `visible()` + rewire | ✅ Done | `scripts/test_unit_docs_parity.py:290`, all four guards read through `read_visible()` |
| T2 - fence-aware `section()` | ✅ Done | `scripts/test_unit_docs_parity.py:724`; but the shipped-doc P7 replay is a weaker probe than the one it claims (see P2 AC 3) |
| T3 - `fenced_commands()` | ✅ Done | `scripts/test_unit_docs_parity.py:780`, three guards fenced, H row left inline |
| T4 - `negated_by()` + vocabulary | ⚠️ Partial | `scripts/test_unit_docs_parity.py:756`; the clause rule (AC 5) has no discriminating test and the inline guard's negation check is inert (AC 7) |

---

### Spec-Anchored Acceptance Criteria

#### P1: A guard rejects a document that does not instruct

| Criterion | Spec-defined outcome | `file:line` + assertion | Outcome |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - ignore every `<!-- ... -->` span, incl. multi-line | every span removed | `scripts/test_unit_docs_parity.py:302` - `re.sub(r"<!--.*?(?:-->|\Z)", "", text, flags=re.DOTALL)`; `:680` - `assertEqual(visible("keep <!-- drop --> keep"), "keep  keep")`; `:683` - `assertEqual(visible("a\n<!-- one\ntwo\nthree -->\nb"), "a\n\nb")` | ✅ PASS |
| AC 2 - command only inside a comment ⇒ guard fails, naming the document | fail + document named | `scripts/test_unit_docs_parity.py:459` - `assertNotIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`; guard `:435-442`. Sensor P2 killed `test_the_halt_field_section_names_the_command` | ⚠️ Spec-precision gap - fails correctly, but the message names the **scope** (`"the `halt` field section"`, `:441`), never the document path |
| AC 3 - fenced-artifact guard fails when the command is prose-only | fail + document named | `scripts/test_unit_docs_parity.py:376` - `haystack = collapsed(fenced_commands(scope) if fenced else scope)`; `:597` - `assertNotIn("thing --flag", fenced_commands(self.DOC))`; `:624` - `assertNotIn(cmd, collapsed(fenced_commands(rescoped)))`. Sensor A10 killed the guard | ⚠️ Spec-precision gap - same naming caveat as AC 2 |
| AC 4 - negated introducing clause ⇒ guard fails, naming the marker | fail + marker named | `scripts/test_unit_docs_parity.py:383` - `marker = negated_by(scope, command)` / `:384` - `assertIsNone(marker, ...{marker!r}...)`; `:521` - `assertEqual(negated_by(body, self.COMMAND), "never run")`; `:531` - same for P1b. Sensor P1/P1b killed `test_the_halt_phase_names_the_command` | ❌ GAP - holds only for a backslash-continued command. Sensor A7: a **one-line** command with `never run:` directly above leaves the guard green (see Gap 2) |
| AC 5 - read only the clause after the final `". "` | an earlier sentence's wording cannot flag a correct instruction | `scripts/test_unit_docs_parity.py:772` - `clause = " ".join(lines[max(0, number - 4):number]).lower().rsplit(". ", 1)[-1]`; test `:535-545` - `assertIsNone(negated_by(body, "...--halt executor"))` | ❌ GAP - vacuous. Sensor H8 survived; the assertion holds for window widths 3-20 with and without the clause split, and for an **empty** vocabulary (see Gap 1) |
| AC 6 - vocabulary is verb-specific **and** flags no shipped fence | 0 offenders; only verb-specific markers | flags-none: `scripts/test_unit_docs_parity.py:580` - `assertEqual(offenders, [], ...)`, independently re-derived → 0 offenders. verb-specific: `:561` - `assertIn(marker.split()[-1], IMPERATIVE_VERBS, marker)` | ⚠️ Split - the "flags none" half is real and sensitive; the "verb-specific" half is **tautological** (`NEGATED_IMPERATIVES` is built from `IMPERATIVE_VERBS` by comprehension at `:749-753`). Sensor H10 survived |
| AC 7 - inline guard applies criteria 1, 2, 4 and does **not** require a fence | negation still rejected on the inline mention | `scripts/test_unit_docs_parity.py:426` - `read_visible(...)` (crit. 1-2 ✅); `:432` - `fenced=False` (no fence required ✅); `:383` - `negated_by(scope, command)` (crit. 4 wired) | ❌ GAP - criterion 4 is **structurally inert**. `table_row()` (`:817`) returns one line, and `negated_by`'s clause window `lines[n-4:n]` is empty at `n=0`, so it always returns `None`. Sensor A8 survived (see Gap 3) |

#### P2: A fenced `#` does not truncate a scope

| Criterion | Spec-defined outcome | `file:line` + assertion | Outcome |
| --------- | -------------------- | ----------------------- | ------ |
| AC 1 - section scan ignores lines inside fences | fenced lines skipped when locating the terminator | `scripts/test_unit_docs_parity.py:724-728` - `fenced = _fenced(lines)` / `if number in fenced: continue`; `:646` - `assertIn("more first-section text", body)`. Sensor H3 killed | ✅ PASS |
| AC 2 - section still extends to the next real heading | scope reaches the next real heading, stops there | `scripts/test_unit_docs_parity.py:650` - `assertNotIn("## second", body)`; `:654` - `assertIn("# not a heading", section(self.DOC, "## first", "fake.md"))`. Sensor H3/H9 killed | ✅ PASS |
| AC 3 - guards inside such a section still pass on the shipped documents | Phase H guard passes, scope still ends at `### Step 3` | `scripts/test_unit_docs_parity.py:669` - `assertIn(cmd, collapsed(fenced_commands(body)))` and `:673` - `assertNotIn("### Step 3", body)` | ⚠️ Spec-precision gap - behaviour is correct (sensor P7 with a true column-0 `#` survives), but the test injects an **indented** `   # resolve the cause first` (`:662`), which already passed under `main`'s `section()`. It is not a replay of P7 (see Gap 4) |

**Status**: ❌ Gaps present - 3 ❌ GAP, 4 ⚠️ spec-precision, 3 ✅ PASS across 10 criteria.

---

### Edge Cases

- [x] **Unterminated `<!--` hides the remainder** - `scripts/test_unit_docs_parity.py:302` (`(?:-->|\Z)`); `:688` - `assertEqual(visible("shown\n<!-- swallowed\nalso swallowed"), "shown\n")`. Sensor H1/H2 killed.
- [x] **Command in a comment *and* in a live fenced block ⇒ pass** - `scripts/test_unit_docs_parity.py:468` - `assertIn("update_loop.py <feature> --root <root> --resume", collapsed(scoped))`. Sensor H2 killed.
- [x] **No fenced block at all ⇒ fail, not raise** - `scripts/test_unit_docs_parity.py:794-797` returns `""`; `:603` - `assertEqual(fenced_commands("## s\n\njust prose, no block\n").strip(), "")`; end-to-end path exercised by sensor A10. ⚠️ the "names the document" half is the same scope-vs-path caveat as AC 2/3.
- [x] **Negated fence + a second affirmative instance ⇒ pass** - `scripts/test_unit_docs_parity.py:551-555` appends a real fenced affirmative copy, `:556` - `assertIsNone(negated_by(rescued, self.COMMAND))`. Sensor H6 killed. ⚠️ but sensor A9 shows an affirmative instance in **prose** also rescues, which AC 3 says must not count as an instruction (Gap 5).
- [x] **Vocabulary matches no fence in any shipped document, asserted by a test** - `scripts/test_unit_docs_parity.py:565-584`, `assertEqual(offenders, [], ...)`. Independently re-derived: 0 offenders with the shipped vocabulary, 15 offenders with a bare-negation-word list - the verb-specific choice is measured and correct.

---

### Discrimination Sensor

**Isolation**: detached `git worktree add --detach` at `a82c10e`, removed with
`git worktree remove --force`. Real tree `git status --porcelain` was **empty
before and empty after**; `git worktree list` shows only the primary tree. No
`git stash` used. Sensor run is valid.

#### Original probes from `.specs/features/halt-resume/validation.md`

| # | Mutation | Expect | Outcome | Guard under test failed? |
| - | -------- | ------ | ------ | ------------------------ |
| P1 | Phase H intro → `"Never run this, it is not a supported operation:"` | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P1b | Phase H intro → `"A human deletes \`loop.json\` and starts over. Whatever you do, never run:"` | kill | ✅ Killed | **YES** - `test_the_halt_phase_names_the_command` |
| P2 | `## \`halt\`` block wrapped in an HTML comment | kill | ✅ Killed | **YES** - `test_the_halt_field_section_names_the_command` |
| P7 | column-0 `# resolve the cause first` inside the Phase H fence | **survive** | ✅ Survived | n/a - false-positive direction, correctly no longer fails |

#### Attacks on the new helpers (document mutations)

| # | Mutation | Expect | Outcome | Guard failed? |
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

#### Helper-logic mutations

| # | Mutation (`scripts/test_unit_docs_parity.py`) | Outcome | Killed by |
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

#### Pre-existing guards (regression - did this feature weaken anything?)

| # | Mutation | Outcome | Killed by |
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
**Outcome**: 24 behaved as expected; **4 unexpected** (A6 false positive, A8 / H8 / H10 survived), **6 partial** (A1, A2, A3, A5, A7, A9 - suite red only via probe-anchor tests, the guard itself stayed green) - **FAIL**

---

### Gate Check

- **Gate command**: `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- **Exit code**: **0**
- **Outcome**: **601 passed, 0 failed, 0 skipped** (212.3s)
- **Test count before feature** (`main`, `700436c`): 496 unit; parity module 35
- **Test count after feature** (`a82c10e`): 519 unit; parity module 58; 601 total
- **Delta**: **+23 unit tests**, all inside `scripts/test_unit_docs_parity.py`
- **Tests deleted**: none. **Assertions weakened**: none - see below.

---

### Weakening Analysis (`main` vs `HEAD`, the four guard bodies)

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

### Code Quality

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

### Fix Plans

#### Gap 1 (Major) - AC 5 is vacuous, and its stated rationale is false

- **Root cause**: `spec.md:48` and the docstring at `scripts/test_unit_docs_parity.py:759-761` justify the clause split with *"a 3-line window flags `SKILL.md:237`"*. It does not: `SKILL.md:235` says **"do not retry"**, and `retry` is not in `IMPERATIVE_VERBS` (`:747`), so no window width can ever flag it. Re-derived independently: for all four shipped scopes, windows of 3/4/6/10/20 lines with and without the clause split all return `None`.
- **Fix task**: either (a) drop the clause split and keep the window, simplifying `:772`, or (b) keep it and add a test that actually distinguishes the two - a fixture whose earlier sentence contains a real vocabulary marker (e.g. `"Never use the editor. Lift the halt with:"`) asserted `None` under clause-scope. Correct the false claim at `spec.md:48`.
- **Priority**: Major

#### Gap 2 (Major) - AC 4 fails for a one-line command

- **Root cause**: `scripts/test_unit_docs_parity.py:772` anchors the clause window to the **scan window start** (`lines[n-4:n]`), not to the command's own line, and `:774-775` returns `None` on the first matching window with a clean clause. For a command on a single line `L`, the earliest matching window starts at `L-2`, so its clause window `lines[L-6:L-2]` excludes the fence opener *and* the introducing clause. Verified directly: negation directly above a one-line command → `negated_by` returns `None`; the two-, three-line and blank-line-gap variants are all caught. The guard works today only because both shipped commands use a backslash continuation.
- **Fix task**: anchor the clause window to the line where the command's **first** token appears, and scan all occurrences before deciding, rather than short-circuiting on the earliest window.
- **Priority**: Major

#### Gap 3 (Major) - AC 7's negation criterion is inert on the inline guard

- **Root cause**: `table_row()` (`:817`) returns exactly one line; `negated_by`'s clause window at `:772` is `lines[max(0,n-4):n]`, which is empty at `n=0`. The call at `:383` therefore always yields `None` for the H transition row. Sensor A8 (`| \`H\` | ... never run update_loop.py --resume |`) passes the whole suite - the same inverted-instruction failure mode as P1b, on the one guard `spec.md:75` singles out.
- **Fix task**: make `negated_by` also read the text **preceding the command on its own line**, then add a test that the H row rejects an inline negated mention.
- **Priority**: Major

#### Gap 4 (Minor) - P2 AC 3's shipped replay is not a replay of P7

- **Root cause**: `scripts/test_unit_docs_parity.py:662` injects `   # resolve the cause first` (3-space indent). `main`'s `section()` searched for `"\n" + "#"*d + " "`, so an indented `#` never truncated anything - re-ran both: indented variant PASSes on `main` **and** on `HEAD`; column-0 variant FAILs on `main` and PASSes on `HEAD`. The behaviour is fixed (sensor P7 confirms), but this test does not evidence it and would still pass if `section()` regressed for indented input.
- **Fix task**: change `:662` to inject the comment at column 0.
- **Priority**: Minor

#### Gap 5 (Minor) - an affirmative *prose* mention rescues a negated fence

- **Root cause**: `assert_instructs` (`:376`) narrows the presence check to `fenced_commands(scope)` but passes the **unfenced** `scope` to `negated_by` at `:383`. A document whose only fenced instruction is negated, but which mentions the command affirmatively in prose, passes (sensor A9). AC 3 says prose is not an instruction; the negation path does not honour that.
- **Fix task**: run the "is there an un-negated occurrence" search over the fenced text when `fenced=True`.
- **Priority**: Minor

#### Gap 6 (Minor) - `_fenced()` has no unterminated-fence rule

- **Root cause**: `_fenced()` (`:924-934`) toggles on each `` ``` `` and never reconciles an odd count, so an unclosed fence marks the rest of the document as fenced - `section()` runs to EOF and `fenced_commands()` accepts a command from any later section. `visible()` handles the analogous unterminated-comment case explicitly (`:302`). Sensor A2 is caught today only incidentally, by `test_each_scope_excludes_the_passage_that_follows_it`.
- **Fix task**: decide and record the intended behaviour for an odd fence count; add the edge case to `spec.md`.
- **Priority**: Minor

#### Gap 7 (Cosmetic) - `fenced_commands()` concatenates all fences in a scope

- **Root cause**: `:794-797` joins every fence body, so `collapsed()` can assemble one command from two separate fences (sensor A3). Requires a contrived document.
- **Priority**: Cosmetic

#### Gap 8 (Minor) - `visible()` strips HTML comments inside code fences

- **Root cause**: `:302` runs over the whole text with no fence awareness. A bash example containing `<!--` silently deletes a span, and an unpaired `<!--` deletes the rest of the document - the same false-positive class this feature exists to remove (P7). Sensor A6 turns a valid document red. Confirmed **no shipped document currently has `<!--` inside a fence**, so this is latent.
- **Fix task**: skip `_fenced()` lines in `visible()`, or add a test pinning the current behaviour as intended.
- **Priority**: Minor

---

### Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| INTENT-01 (P1 AC 1, 2 - HTML comments) | Implementing | ✅ Verified |
| INTENT-02 (P1 AC 3, 7 - fence required / inline exempt) | Implementing | ❌ Needs Fix - AC 7 criterion 4 inert (Gap 3) |
| INTENT-03 (P1 AC 4, 5, 6 - negation vocabulary) | Implementing | ❌ Needs Fix - Gaps 1, 2 |
| INTENT-04 (P2 AC 1, 2, 3 - fence-aware section) | Implementing | ✅ Verified (test-quality note: Gap 4) |

---

### Summary

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
