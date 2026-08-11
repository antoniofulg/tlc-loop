# Parity Guards Prove Intent Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/parity-intent/spec.md`
**Design**: none - no architectural decision. Four helpers in one existing test module, built on the `_fenced()` line scan already there.
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: **none** - no `AGENTS.md`, `CONTRIBUTING.md`, `Makefile`, `pyproject.toml`, or CI workflow. Inherited from `.specs/features/halt-resume/tasks.md`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Parity-scan helper (`visible`, `section`, `fenced_commands`, `negated_by`) | unit | Every branch; each helper proven to discriminate against the mutation it exists to catch, and proven not to fire on the shipped corpus | `scripts/test_unit_docs_parity.py` | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |
| Prose (`SKILL.md`, `references/`) | unit | Unchanged by this feature; the existing guards must keep passing on the shipped text | `scripts/test_unit_docs_parity.py` | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |

**Self-test note.** This feature's code *is* test code, so "the tests" are the helpers' own discrimination tests: each task plants the mutation its helper targets, asserts the guard fails, and asserts the shipped corpus still passes. A helper that cannot be shown to fail on its mutation is not done.

**Baseline (measured before Execute):** 490 unit + 88 integration = 578 total, all passing. Quick gate ~100-160s, full gate ~160-190s - both exceed a 120s command timeout, so gates run with an extended timeout.

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |
| Full | After tasks with integration tests | `python3 -m unittest discover -s scripts -p 'test_*.py'` |
| Build | After phase completion | `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'` |

**Tools note:** no MCP server is required. Filesystem and shell access only.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: The reader's view

Two scans that currently read text the reader never sees, and structure the reader never wrote. Both are corrections to what the scan looks at, before anything is asserted about it.

```
T1 → T2
```

### Phase 2: The instruction is an instruction

Presence is not instruction. These two make the command guards assert the thing their criteria actually name.

```
T3 → T4
```

---

## Task Breakdown

### T1: Make HTML comments invisible to the scans ✅

**What**: Add a `visible()` helper that strips every `<!-- ... -->` span, and route the four command guards through it.
**Where**: `scripts/test_unit_docs_parity.py`
**Depends on**: None
**Reuses**: `read_shipped()` (`scripts/test_unit_docs_parity.py:285`) as the single read point the helper wraps.
**Requirement**: INTENT-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `visible()` removes single-line and multi-line `<!-- ... -->` spans (P1 AC 1)
- [ ] An unterminated `<!--` renders the rest of the document invisible, rather than being ignored (spec Edge Cases)
- [ ] The four command guards read through `visible()`, so a command surviving only inside a comment fails the guard naming the document (P1 AC 2)
- [ ] Probe P2 replayed: wrapping the `` ## `halt` `` block in an HTML comment fails its guard
- [ ] A command present both in a comment and in a live block still passes (spec Edge Cases)
- [ ] The shipped documents still pass, including `assets/iteration-summary.template.md`, which uses HTML comments legitimately
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 494 unit tests pass (unit baseline 490 + ≥4), no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `test(docs-parity): hide html comments from the command guards`

---

### T2: Make the section scan fence-aware ✅

**What**: Have `section()` skip lines inside fenced blocks when looking for the heading that ends a section.
**Where**: `scripts/test_unit_docs_parity.py`
**Depends on**: T1
**Reuses**: `_fenced()` (`scripts/test_unit_docs_parity.py:582`), which already returns the fenced line indices for the `no_diff_tasks` scan.
**Requirement**: INTENT-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `section()` ignores fenced lines when locating the terminating heading (P2 AC 1)
- [ ] A section whose fenced block contains a column-0 `#` still extends to the next real heading (P2 AC 2)
- [ ] Probe P7 replayed: inserting `# a comment` inside the Phase H bash block leaves the Phase H guard passing and the scope still ending at `### Step 3` (P2 AC 3)
- [ ] `_fenced()` is reused rather than reimplemented, and the existing `no_diff_tasks` scan that depends on it is untouched
- [ ] The bound established in `halt-resume` still holds: the Phase H scope excludes `### Step 3`, and the `` ## `halt` `` scope excludes `` ## `iterations[]` ``
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 497 unit tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `test(docs-parity): keep a fenced hash from truncating a section`

---

### T3: Require a fenced artifact where the criterion names one

**What**: Add a `fenced_commands()` helper returning only the commands inside fenced blocks, and assert against it in the three guards whose artifact is a fenced call.
**Where**: `scripts/test_unit_docs_parity.py`
**Depends on**: T2
**Reuses**: `_fenced()` and `collapsed()` (`scripts/test_unit_docs_parity.py:456`).
**Requirement**: INTENT-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The `` ## `halt` `` , Phase H and Phase B guards assert their command inside a fenced block, not anywhere in the scope (P1 AC 3)
- [ ] Moving a required command out of its fence into surrounding prose fails the guard naming the document (P1 AC 3)
- [ ] The `H` transition-row guard is left asserting an inline mention and does **not** require a fence, because its artifact is a table cell (P1 AC 7)
- [ ] A scope with no fenced block at all fails rather than raising, and the failure names the document (spec Edge Cases)
- [ ] `collapsed()` still flattens the backslash continuation, so the multi-line call still matches
- [ ] The shipped documents still pass
- [ ] Gate check passes: `python3 -m unittest discover -s scripts -p 'test_unit_*.py'`
- [ ] Test count: ≥ 501 unit tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: quick

**Commit**: `test(docs-parity): require the command where the criterion names a fence`

---

### T4: Reject a command its introducing clause negates

**What**: Add the negated-imperative vocabulary and a `negated_by()` helper reading the clause before the fence, and fail the four command guards when it matches.
**Where**: `scripts/test_unit_docs_parity.py`
**Depends on**: T3
**Reuses**: `fenced_commands()` from T3 for fence positions; `visible()` from T1.
**Requirement**: INTENT-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The vocabulary holds only verb-specific negated imperatives (`never run`, `do not call`, `don't use`, ...), never bare negation words (P1 AC 6)
- [ ] `negated_by()` reads only the clause after the final `". "` before the fence (P1 AC 5)
- [ ] A guard whose command is introduced by a matching clause fails, and the failure names the marker matched (P1 AC 4)
- [ ] Probe P1 replayed: "Never run this, it is not a supported operation" before the Phase H block fails the guard
- [ ] Probe P1b replayed: "A human deletes `loop.json` and starts over. Whatever you do, never run:" fails the guard
- [ ] `SKILL.md:237` stays affirmative: "do not retry - a timeout is an executor failure, not a flake:" introduces a correct `--halt executor` instruction and must not be flagged (P1 AC 5)
- [ ] A test asserts the vocabulary matches **no** fence in any shipped document, so extending the list later cannot silently break valid prose (P1 AC 6, spec Edge Cases)
- [ ] A negated instance plus a second affirmative instance in the same scope still passes (spec Edge Cases)
- [ ] The residual risk - a negation phrased outside the vocabulary still passes - is stated in the test docstring, not left for the reader to discover
- [ ] Gate check passes: `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'`
- [ ] Test count: ≥ 595 total tests pass, no existing test deleted or weakened

**Tests**: unit
**Gate**: build

**Commit**: `test(docs-parity): fail a command its introducing clause negates`

---

## Phase Execution Map

```
Phase 1 → Phase 2

Phase 1:  T1 ------→ T2
Phase 2:  T3 ------→ T4
```

Execution is strictly sequential. 4 tasks pack into a single batch, so Execute runs inline in the main window with no sub-agents dispatched. The Verifier still runs after the final task.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `visible()` + rewire | 1 helper, 1 file | ✅ Granular |
| T2: fence-aware `section()` | 1 helper, 1 file | ✅ Granular |
| T3: `fenced_commands()` + rewire 3 guards | 1 helper, 1 file | ✅ Granular |
| T4: vocabulary + `negated_by()` | 1 helper + 1 constant, 1 file | ✅ Granular |

Each task builds one helper and rewires the guards that need it in the same commit. Splitting helper from rewiring would leave a commit whose helper is dead code and whose guards still carry the hole.

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | phase-1 head | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | phase-2 head, T2 → T3 across the phase boundary | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |

No dependency points to a later phase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Parity-scan helper (`visible`) | unit | unit | ✅ OK |
| T2 | Parity-scan helper (`section`) | unit | unit | ✅ OK |
| T3 | Parity-scan helper (`fenced_commands`) | unit | unit | ✅ OK |
| T4 | Parity-scan helper (`negated_by`) | unit | unit | ✅ OK |

No task carries `Tests: none`. Each helper's discrimination test - the planted mutation it must fail on - ships in the same commit as the helper.

---

## Requirement Coverage

| Requirement ID | Tasks | Status |
| --- | --- | --- |
| INTENT-01 | T1 | Verified in T1 |
| INTENT-02 | T3 | Pending |
| INTENT-03 | T4 | Pending |
| INTENT-04 | T2 | Verified in T2 |

**Coverage:** 4 total, 4 mapped to tasks, 0 unmapped.
