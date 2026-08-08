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

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
