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

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
