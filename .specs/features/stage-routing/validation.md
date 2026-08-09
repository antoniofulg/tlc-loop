# Stage Routing Validation

## Validation: stage-routing - PASS

**Verdict**: PASS
**Date**: 2026-08-09
**Spec source**: `.specs/features/stage-routing/plan.md`, Section 9
**Diff range**: `8bf6e50^..HEAD`
**Verifier**: independent verifier; author != verifier

## Scope adaptation

No `spec.md` or `tasks.md` exists for this feature. The acceptance criteria are
therefore derived from Section 9 of `plan.md` (`plan.md:702-715`), with the
implementation/test matrix in Sections 4-6 as supporting evidence. This is an
explicit validation adaptation, not a product gap.

## Task completion

The seven plan tasks are represented by the seven commits in the requested diff:
T1 `8bf6e50`, T2 `0aed4b6`, T3 `6870f4c`, T4 `a312cc4`, T5 `347fe24`, T6
`cfbab8d`, T7 `877cc75`. No task artifact exists to mark separately.

## Acceptance criteria, evidence-or-zero

| Criterion from plan Section 9 | Expected outcome | Evidence (`file:line` + assertion) | Result |
| --- | --- | --- | --- |
| Dual-skill short form has complete opt-in meaning | `$tlc-loop` contributes the routing contract only when named beside `$tlc-spec-driven`; Tasks ownership and approval remain with `tlc-spec-driven`; Execute does not start | `SKILL.md:39-49`; `references/tasks-routing-contract.md:3-13,120-131`; parity assertions `scripts/test_unit_docs_parity.py:252-271,291-296` | PASS |
| Phase titles do not control routing | Route is read from declared `Stage`, never inferred from title | `_tasksmd.py:206-223`; `_routing.py:22-57`; explicit-stage assertions `scripts/test_unit_routing.py:26-40` | PASS |
| Every dispatch route appears as `stage=` | Phase-B output carries the effective stage and detector uses it in the batch record | `detect_phase.py:234-251`; exact assertions `scripts/test_unit_detect_phase.py:291-299,314-320`; contract `references/phase-transitions.md:64-67` | PASS |
| Batches are homogeneous by effective stage | Stage change closes a batch; equal stages may share it; phase remains whole | `_batching.py:58-83`; assertions `scripts/test_unit_batching.py:130-165` | PASS |
| `strict_routing=true` works with explicit Foundation | Missing Stage errors in strict mode; explicit Foundation route succeeds | `_routing.py:29-43`; bootstrap tests `scripts/test_unit_init_loop.py:260-326`; four-stage strict E2E `scripts/test_int_end_to_end.py:329-356` | PASS |
| Unknown/reserved stages never use fallback | Fallback applies only to absent Stage in non-strict mode; malformed, unknown, reserved, and typo values error | `_routing.py:39-57`; tests `scripts/test_unit_routing.py:52-84`; contract `references/tasks-routing-contract.md:65-79` | PASS |
| Phase number is positive integer and unique; `Stage` is first non-empty line and non-duplicate | `Phase 2a`, duplicate numbers, misplaced Stage, and duplicate Stage are rejected | `_tasksmd.py:32-35,68-114`; assertions `scripts/test_unit_tasksmd.py:247-274` | PASS |
| `verify` and `fix` retain their runtime roles | Both remain reserved implementation stages; Verify and Fix remain separate loop phases | `_routing.py:10-11,44-46`; `SKILL.md:265-305`; contract `references/tasks-routing-contract.md:78-79` | PASS |
| Bootstrap prints route map and refuses invalid routing before state | Map prints effective provider/model; aggregated route errors return before `loop.json` creation | `init_loop.py:101-114,202-236`; assertions `scripts/test_unit_init_loop.py:260-326` | PASS |
| Resolver uses the detected stage | Phase B resolves `--stage <stage-from-detect-line>` exactly; no title/default recomputation | `SKILL.md:204-215`; `references/executors.md:124-144`; resolver domain-stage test `scripts/test_unit_resolve_stage.py:91-99` | PASS |
| Documentation is updated and remains in parity | Contract, schema, examples, README, checklist, executors, and transitions describe staged routing and new vocabulary | `references/tasks-routing-contract.md:23-46,65-79,120-131`; parity assertions `scripts/test_unit_docs_parity.py:252-296` | PASS |
| E2E covers four stages | Foundation, backend, frontend, docs advance as four ordered batches, each with matching `stage=` | `scripts/test_int_end_to_end.py:329-356` exact batch assertions | PASS |
| Legacy tasks remain compatible | With strict off, absent Stage maps to `implement` and preserves prior batches/dispatch | `_config.py:61-70`; `_batching.py:31-39`; assertions `scripts/test_unit_batching.py:161-165`, `scripts/test_unit_detect_phase.py:314-320`, `scripts/test_unit_init_loop.py:277-284` | PASS |
| No `tlc-spec-driven` change is required for opt-in | Contract is supplied by `tlc-loop`; sibling authoring ownership is unchanged | `SKILL.md:39-49`; `references/tasks-routing-contract.md:3-6`; diff range contains only the `tlc-loop` tree plus this plan | PASS |

**Spec-anchored result**: 14/14 plan criteria covered with file/line evidence;
0 spec-precision gaps.

## Gate checks

Commands were run exactly as required.

| Gate | Result |
| --- | --- |
| `rtk proxy python3 -m unittest discover -s scripts -p 'test_unit_*.py'` | PASS, 364 tests, 0 failures, 0 skips (`Ran 364 tests in 53.940s`) |
| `rtk proxy python3 -m unittest discover -s scripts -p 'test_*.py'` | PASS, 434 tests, 0 failures, 0 skips (`Ran 434 tests in 75.112s`) |
| `rtk proxy python3 -m compileall -q scripts/` | PASS, exit 0 |
| `rtk proxy bash -n scripts/loop.sh` | PASS, exit 0 |

Baseline supplied by the plan: 327 unit / 396 total. Current counts are 364
unit / 434 total, deltas `+37` / `+38`. No test count decrease, failures, or
skips occurred.

## Discrimination sensor

One high-risk mutation ran in a temporary detached worktree created with
`mktemp -d` and `git worktree add --detach <dir> HEAD`; no `git stash` was used.

| Mutation | Focal result |
| --- | --- |
| Scratch `_routing.py:52-55`: changed an explicit unknown stage from an error to `effective_stage="implement"` | KILLED: `rtk proxy python3 -m unittest discover -s scripts -p 'test_unit_routing.py'` exited 1; `test_unknown_explicit_stage_never_falls_back` and aggregated-errors test failed (`scripts/test_unit_routing.py:52-84`) |

The detached worktree and temporary directory were removed. Real-tree
`git status --porcelain=v1` was empty before and after the sensor, so isolation
held. The only permitted real-tree write is this report.

## Deterministic backing

Pre-report attempt:

`rtk proxy python3 /Users/antoniofulg/.agents/skills/tlc-spec-driven/scripts/validate_state.py stage-routing --root /Users/antoniofulg/orca/workspaces/tlc-loop/cero`

exited 1 with:

`ERROR stage-routing: no validation.md - Execute is not done until the Verifier writes it (author != verifier). Dispatch validation before marking done.`

This was expected because the report did not yet exist and is not a product
gap. After writing this report, the same command passed:

`validate_state: 0 error(s) across [stage-routing]`

## Code quality

| Principle | Result |
| --- | --- |
| No unrequested feature or scope creep | PASS |
| No unnecessary single-use abstraction | PASS |
| Surgical changes and existing style | PASS |
| Test assertions remain specific and non-shallow | PASS |
| Tests map to plan criteria/edge cases | PASS |
| Documented guidelines followed | PASS, `/Users/antoniofulg/.agents/skills/tlc-spec-driven/references/coding-principles.md` |

## Edge cases

- PASS: absent Stage with strict off falls back to `implement`.
- PASS: absent Stage with strict on errors before state.
- PASS: typo/unknown, malformed, duplicate, misplaced, and reserved Stage values
  error without fallback.
- PASS: `Phase 2a`, `Phase 2b`, and duplicate phase numbers are rejected.
- PASS: small tail folds only when effective stage matches; cross-stage tail stays
  separate.
- PASS: legacy no-Stage batching remains unchanged.

## Requirement traceability

No `spec.md` exists to update. All Section 9 criteria are marked **Verified** by
this report; no fix task is required.

## Summary

**Overall**: PASS, ready.

**What works**: explicit opt-in contract, strict/fallback routing, parser
validation, homogeneous batches, detector propagation, bootstrap safety,
stage-based resolver dispatch, documentation parity, four-stage E2E, and legacy
compatibility.

**Issues found**: none.

**Next step**: none. The final `validate_state.py` backing gate passed.
