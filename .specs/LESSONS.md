# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - When an AC says SHALL record, name the component that writes it and the field it writes; a read-only detector cannot satisfy a recording clause.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `scripts/detect_phase.py` · harmful: 0
- features: tlc-loop
- evidence: LOOP-01 AC 5b (spec.md:78) (scripts/detect_phase.py)
- last seen: 2026-08-08T16:06:13Z

### L-002 - A value a helper returns is not reported until a consumer emits or stores it; assert the emitted output, not the helper's return, when a doc claims it is reported.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `scripts/detect_phase.py` · harmful: 0
- features: tlc-loop
- evidence: scripts/detect_phase.py:147 vs references/phase-transitions.md:108 (scripts/detect_phase.py)
- last seen: 2026-08-08T16:06:25Z

### L-003 - A task that adds an enum value must re-run the enum-parity check across every document that enumerates it, or pin the parity as a test.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `SKILL.md` · harmful: 0
- features: tlc-loop
- evidence: SKILL.md:290-291 vs scripts/update_loop.py:43-52 (SKILL.md) (+1 more)
- last seen: 2026-08-08T22:46:50Z

### L-004 - Validating the same constraint in two layers can make the inner one unreachable; check reachability from the outer layer's legal input set before writing the inner test.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `scripts/resolve_stage.py` · harmful: 0
- features: tlc-loop
- evidence: LOOP-05 AC 2 (spec.md:163) (scripts/resolve_stage.py)
- last seen: 2026-08-08T16:06:25Z

### L-005 - When a change makes a cached file hold a fact that cannot be rebuilt from source, retract every sentence that calls the file disposable; adding a new paragraph does not withdraw the old one.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `references/state-schema.md` · harmful: 0
- features: tlc-loop
- evidence: references/state-schema.md:15 and :82 vs :169 (added by c7d4cfe) (references/state-schema.md)
- last seen: 2026-08-08T22:46:49Z

### L-006 - A new document that restates a claim from an existing one inherits its errors; verify each claim against the code path, and search the test suite for an assertion that contradicts it.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `README.md` · harmful: 0
- features: tlc-loop
- evidence: README.md:143 vs scripts/test_int_end_to_end.py:346 (README.md)
- last seen: 2026-08-08T22:46:49Z

### L-007 - Declare a task's gate at the level that covers every file the task touches; a unit-only gate cannot detect a regression in code that only an integration test exercises.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `scripts/update_loop.py` · harmful: 0
- features: tlc-loop
- evidence: mutant M6: scripts/update_loop.py:153 survives the quick gate declared by T34 (scripts/update_loop.py)
- last seen: 2026-08-08T22:46:50Z

### L-008 - Closing a documentation gap at the reviewer's cited lines is not closing it; grep the claim's distinctive wording across references, code docstrings, and the planning record first.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `references/` · harmful: 0
- features: tlc-loop
- evidence: references/phase-transitions.md:155 (claim survives a7d1460) (references/)
- last seen: 2026-08-08T23:12:42Z

### L-009 - When an edit changes a list's count or membership, re-read every nearby sentence that refers to it by count or position; those references do not update themselves.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `references/state-schema.md` · harmful: 0
- features: tlc-loop
- evidence: references/state-schema.md:89 vs :84-87 (references/state-schema.md)
- last seen: 2026-08-08T23:12:42Z

### L-010 - Put a timeout's force-kill inside the watchdog itself, never after the wait it is meant to rescue; anything that blocks that wait disables the escalation entirely.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `shell/process-supervision` · harmful: 0
- features: tlc-loop
- evidence: scripts/loop.sh:123-138 (LOOP-06 executor_timeout_seconds) (shell/process-supervision)
- last seen: 2026-08-09T05:57:53Z

### L-011 - Backgrounding a child into its own process group changes its terminal semantics: redirect its stdin, or a tty read stops the job, SIGTERM only queues, and the parent's wait never returns.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `shell/process-supervision` · harmful: 0
- features: tlc-loop
- evidence: scripts/loop.sh:108-119 (LOOP-06 executor_timeout_seconds) (shell/process-supervision)
- last seen: 2026-08-09T05:57:53Z

### L-012 - Killing a helper subshell does not kill the command it forked; signal the process group or the child outlives the parent and keeps holding its inherited stdout.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `shell/process-supervision` · harmful: 0
- features: tlc-loop
- evidence: scripts/loop.sh:116-127 (LOOP-06 executor_timeout_seconds) (shell/process-supervision)
- last seen: 2026-08-09T05:57:53Z

### L-013 - A cleanup step nothing observes is untested however obviously correct it looks; assert the process, file, or handle is gone after the happy path, not only that the result was right.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `testing/resource-cleanup` · harmful: 0
- features: tlc-loop
- evidence: M13 scripts/loop.sh:126-127 (survived 372/372) (testing/resource-cleanup)
- last seen: 2026-08-09T05:57:53Z

### L-014 - A change that inverts a mechanism obliges a sweep of every document that explains that mechanism, not only those repeating a retracted sentence; a scanner keyed on phrasing cannot see a stale explanation.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `docs/parity` · harmful: 0
- features: tlc-loop
- evidence: references/phase-transitions.md:139-143,228 (LOOP-02 AC 6 after T37) (docs/parity)
- last seen: 2026-08-09T05:57:53Z

### L-015 - A document that claims a property of every member of a family needs a test that iterates the family; one written for the member you last touched leaves the others unverified.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `docs/parity` · harmful: 0
- features: tlc-loop
- evidence: references/providers.md:195-198 vs scripts/resolve_stage.py:76-91 (docs/parity)
- last seen: 2026-08-09T07:33:58Z

### L-016 - A phrase-list scanner is not repaired by adding phrases; anchor the check on a structural invariant the wording cannot evade, or the same stale claim ships again in new words.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `docs/parity` · harmful: 0
- features: tlc-loop
- evidence: references/state-schema.md:225-226 (T42 Done-when 3 falsified) (docs/parity)
- last seen: 2026-08-09T07:33:58Z

### L-017 - Test teardown that signals a fixture must send the one signal the fixture cannot ignore; a probe built to ignore SIGTERM outlives a SIGTERM-based cleanup exactly when the test fails.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `testing/resource-cleanup` · harmful: 0
- features: tlc-loop
- evidence: scripts/test_unit_spawn.py:73-75 (11 probes leaked during the round-6 sensor) (testing/resource-cleanup)
- last seen: 2026-08-09T07:33:58Z

### L-018 - Once wait() returns, the reaped pid may already belong to something else: do not signal it again, and catch every errno the signal call can raise, not only no-such-process.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `shell/process-supervision` · harmful: 0
- features: tlc-loop
- evidence: scripts/_spawn.py:57-62,70-81 (LOOP-05 AC 5: expiry exits non-zero, halt not recorded) (shell/process-supervision)
- last seen: 2026-08-09T08:37:23Z

### L-019 - When a mitigation covers one dispatch path only, state what the other path does; a hazard note scoped to one branch is read as covering both, especially when the uncovered branch is the default.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `docs/hazards` · harmful: 0
- features: tlc-loop
- evidence: LOOP-05 AC 3 (spec.md:164) vs README.md:175-185 (docs/hazards)
- last seen: 2026-08-09T08:37:23Z

### L-020 - Replacing a duplicated claim with one canonical section removes the drift but asserts nothing; pin the structure itself - one full explanation, every other mention a link - or the convention is held by memory again.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `docs/parity` · harmful: 0
- features: tlc-loop
- evidence: M11 references/state-schema.md:243-245 (survived 396/396) (docs/parity)
- last seen: 2026-08-09T08:37:24Z

### L-021 - When an acceptance criterion scopes a documentation requirement to a named section, assert the needle inside that section, not across the whole file
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: halt-resume
- evidence: scripts/test_unit_docs_parity.py:377-389 (mutants M11b, M12, M14) (docs-parity)
- last seen: 2026-08-11T14:01:35Z

### L-022 - A documentation guard that matches a command as a substring passes on a negated or commented-out copy of it, so bind the match to the affirmative instruction rather than to the characters
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: halt-resume
- evidence: scripts/test_unit_docs_parity.py:456-463 (mutants P1, P1b, P2) (docs-parity)
- last seen: 2026-08-11T14:25:09Z

### L-023 - A test helper that returns the first matching line or heading binds the assertion to whichever passage comes first, so raise when more than one matches instead of silently picking one
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `test-helpers` · harmful: 0
- features: halt-resume
- evidence: scripts/test_unit_docs_parity.py:466-471 (mutant P3) (test-helpers)
- last seen: 2026-08-11T14:25:09Z

### L-024 - When a criterion names a full command and a qualifying clause, assert both, not just the distinguishing flag
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: halt-resume
- evidence: scripts/test_unit_docs_parity.py:389 (mutants P5, P6) (docs-parity)
- last seen: 2026-08-11T14:25:09Z

### L-025 - Anchor a lookbehind scan window to the matched token's own line, not to the enclosing scan window's start.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: parity-intent
- evidence: P1 AC 4 / sensor A7 / scripts/test_unit_docs_parity.py:772 (docs-parity)
- last seen: 2026-08-11T16:14:11Z

### L-026 - Prove a reused check can still fire on the narrowest scope it is applied to, not only on the widest.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: parity-intent
- evidence: P1 AC 7 / sensor A8 / scripts/test_unit_docs_parity.py:383 (docs-parity)
- last seen: 2026-08-11T16:14:11Z

### L-027 - Back a scan-window or scope choice with a fixture whose verdict changes when the window changes.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: parity-intent
- evidence: mutant H8 / scripts/test_unit_docs_parity.py:535 (docs-parity)
- last seen: 2026-08-11T16:14:11Z

### L-028 - Never assert a property that the constant's own construction guarantees; the test cannot fail.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `testing` · harmful: 0
- features: parity-intent
- evidence: mutant H10 / scripts/test_unit_docs_parity.py:558 (testing)
- last seen: 2026-08-11T16:14:11Z

### L-029 - Replay a regression probe with the exact input that originally failed, not a weakened variant.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `testing` · harmful: 0
- features: parity-intent
- evidence: P2 AC 3 / scripts/test_unit_docs_parity.py:662 (testing)
- last seen: 2026-08-11T16:14:11Z

### L-030 - A corpus-wide safety-net test must call the production helper, not re-implement its scan; a private copy drifts the moment the helper changes.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: parity-intent
- evidence: mutants M2/M24/V1 / scripts/test_unit_docs_parity.py:659 (docs-parity)
- last seen: 2026-08-11T17:01:49Z

### L-031 - When a test passes a multi-line literal to a helper that compares against collapsed text, the comparison can never match and the assertion is unfalsifiable.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `test-helpers` · harmful: 0
- features: parity-intent
- evidence: New Gap A / scripts/test_unit_docs_parity.py:535 (test-helpers)
- last seen: 2026-08-11T17:01:49Z

### L-032 - Correcting a false rationale in the spec is half the fix; the same sentence usually also lives in a code comment, and only the spec gets rewritten.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `docs-parity` · harmful: 0
- features: parity-intent
- evidence: spec.md:48 corrected while scripts/test_unit_docs_parity.py:537 kept the retracted claim (docs-parity)
- last seen: 2026-08-11T17:01:49Z

### L-033 - Delete __pycache__ before every mutation run: CPython invalidates bytecode on (mtime, size), so a same-length edit in the same second makes a live mutant look covered.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `testing` · harmful: 0
- features: parity-intent
- evidence: round-2 sensor methodology, reproduced with os.utime (testing)
- last seen: 2026-08-11T17:01:49Z

### L-034 - Test a guard's plumbing through the guard: asserting on the inner helper leaves the wiring in the assert_* wrapper unpinned.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `test-helpers` · harmful: 0
- features: parity-intent
- evidence: mutant M23 / scripts/test_unit_docs_parity.py:376 (test-helpers)
- last seen: 2026-08-11T17:01:49Z

### L-035 - Hunt unfalsifiable tests by subtraction: any test the whole mutant battery never kills is a suspect, and the added-tests list is the set to check.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `testing` · harmful: 0
- features: parity-intent
- evidence: round-3 sensor: 68 mutants vs scripts/test_unit_docs_parity.py:1 (testing)
- last seen: 2026-08-11T17:24:25Z

### L-036 - Give every corpus-wide negative assertion a positive control that fails when the scan reaches no input; assertEqual(offenders, []) is green on an empty corpus.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `test-helpers` · harmful: 0
- features: parity-intent
- evidence: mutant F16 / scripts/test_unit_docs_parity.py:600 (test-helpers)
- last seen: 2026-08-11T17:24:25Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
