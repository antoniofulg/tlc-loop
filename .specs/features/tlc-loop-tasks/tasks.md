# tlc-loop-tasks Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/tlc-loop-tasks/design.md`
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: **none - strong defaults applied**. This is a greenfield repository with no existing tests, no `AGENTS.md`, no `CONTRIBUTING.md`, and no test-runner config. Framework chosen by the user: stdlib `unittest` (Python 3.14.6; `pytest`, `ruff`, and `shellcheck` are not installed). Precedent: `cy-loop-tasks/scripts/test_scripts.py` is stdlib `unittest`, tmpdir-scoped, zero dependencies.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Support module (`_paths`, `_state_io`, `_config`, `_gitio`, `_tasksmd`, `_batching`) | unit | All branches; 1:1 to spec ACs; every listed edge case has a dedicated test | `scripts/test_unit_*.py` | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |
| CLI entrypoint (`detect_phase`, `update_loop`, `checkpoint`, `init_loop`, `resolve_stage`) | unit | Every printed output variant and every non-zero exit path, invoked as a subprocess inside a tmpdir git repo | `scripts/test_unit_*.py` | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |
| Shell driver (`loop.sh`) | integration | Terminates on `phase=E` and on `phase=H`; spawns the resolved respawn command; never loops on a halt | `scripts/test_int_*.py` | `python3 -m unittest discover -s scripts -p 'test_int_*.py'` |
| Cross-script flow (bootstrap → detect → checkpoint → detect) | integration | The full resume path over a real tmpdir git repo, including `loop.json` deletion | `scripts/test_int_*.py` | `python3 -m unittest discover -s scripts -p 'test_int_*.py'` |
| Prose (`SKILL.md`, `references/`, `assets/`) | none | - (build gate only) | - | build gate only |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `python3 -m unittest discover -s scripts -p 'test_unit_*.py'` |
| Full | After tasks with integration tests | `python3 -m unittest discover -s scripts -p 'test_*.py'` |
| Build | After phase completion or prose/config-only tasks | `python3 -m compileall -q scripts/ && bash -n scripts/loop.sh && python3 -m unittest discover -s scripts -p 'test_*.py'` |

**Tools note:** no MCP server is required. Every task uses filesystem and shell access only. No `tlc-spec-driven` sub-skill is invoked from inside a task; the skill governs the cycle, not the task content.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Foundation

Path resolution, state codec, and config parsing. Everything downstream imports these.

```
T1
T2
T3 -> T4
```

### Phase 2: Phase detection

The read-only heart of the loop: derive the next action from git, `tasks.md`, and state.

```
T5 -> T8 -> T9
T6 -> T7 -> T8
```

### Phase 3: State mutation and checkpoint

The two writers, plus bootstrap.

```
T10 -> T13
T11
T12 -> T13
```

### Phase 4: Providers and executors

Discovery first - the adapter table is data, and wrong data breaks every dispatch.

```
T14 -> T15 -> T16 -> T17
```

### Phase 5: Continuation and recovery

```
T18
T19
T20
```

### Phase 6: Skill assembly

```
T21 -> T22
T21 -> T23
T24
```

### Phase 7: Integration and hardening

```
T25 -> T27
T26
T28
```

---

## Task Breakdown

### T1: Resolve sibling skill paths ✅

**What**: Module that resolves this skill's own directory and the sibling `tlc-spec-driven` directory through symlinks.
**Where**: `scripts/_paths.py`
**Depends on**: None
**Reuses**: Nothing - first module.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `skill_dir()` returns this skill's directory resolved with `realpath`, correct when reached through a symlink
- [x] `tlc_dir()` returns the sibling `tlc-spec-driven` directory
- [x] `tlc_script(name)` returns the path to a named script under `<tlc>/scripts/`
- [x] A missing sibling raises with the attempted absolute path in the message, never a bare `FileNotFoundError`
- [x] Unit tests cover: resolution through a symlinked entry, resolution from a real path, and the missing-sibling error text

**Tests**: unit
**Gate**: quick

---

### T2: loop.json state codec ✅

**What**: Strict load/save codec for `loop.json` - the only module that touches the state file.
**Where**: `scripts/_state_io.py`
**Depends on**: None
**Reuses**: Structure of `cy-loop-tasks/scripts/_state_io.py`; stdlib `json`.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `load(feature, root)` parses `loop.json` and raises a descriptive error on malformed JSON or a schema violation
- [x] `save(feature, root, state)` writes atomically (temp file plus rename) with `indent=2` and sorted keys
- [x] `new_state(feature, objective, harness)` returns the documented initial shape
- [x] Schema validation rejects an unknown `status` value and a missing required key
- [x] Unit tests cover: round trip, malformed JSON raising, schema violation raising, and atomicity (no partial file left when the write fails)

**Tests**: unit
**Gate**: quick

---

### T3: TOML config reader with defaults ✅

**What**: Parse `.specs/loop.config.toml` with stdlib `tomllib` and apply documented defaults for every absent key.
**Where**: `scripts/_config.py`
**Depends on**: None
**Reuses**: stdlib `tomllib` (Python 3.11+).
**Requirement**: LOOP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `load_config(root)` returns a fully-defaulted config when the file is absent
- [x] An omitted key under `[limits]` resolves to unlimited, matching the documented TOML-has-no-null rule
- [x] A malformed TOML file raises with the parse error and the file path
- [x] An unknown `effort` value is rejected at load time with the offending stage named
- [x] Unit tests cover: absent file, partial file, malformed file, unknown effort, and the unlimited-by-omission rule

**Tests**: unit
**Gate**: quick

---

### T4: Document the config schema ✅

**What**: Reference documenting every `loop.config.toml` key, its default, and the unlimited-by-omission rule.
**Where**: `references/config-schema.md`
**Depends on**: T3
**Reuses**: Design doc's config section.
**Requirement**: LOOP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Every key implemented in T3 appears with its type, default, and meaning
- [x] The config-versus-state separation rule is stated: the loop reads this file and never writes it
- [x] The TOML-has-no-null convention is documented
- [x] No key is documented that T3 does not implement

**Tests**: none
**Gate**: build

---

### T5: Git trailer read and dedupe ✅

**What**: Helpers to read completed task IDs from commit trailers and to compose the trailer arguments for a commit.
**Where**: `scripts/_gitio.py`
**Depends on**: None
**Reuses**: Verified invocation `git log --format="%(trailers:key=Task,valueonly)"`.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `completed_tasks(root)` returns task IDs from trailers, deduped, preserving first-seen order
- [x] Commits without a `Task:` trailer contribute nothing and produce no empty entries
- [x] A duplicate trailer after a rebase or cherry-pick yields one entry, and the duplication is reported to the caller
- [x] `is_git_repo(root)` reports whether `git rev-parse --git-dir` succeeds
- [x] Unit tests build a real tmpdir repo and cover: no commits, commits without trailers, mixed commits, and a duplicated trailer

**Tests**: unit
**Gate**: quick

---

### T6: Parse tasks.md ✅

**What**: Extract task IDs, their phase, and their `Depends on` / `Tests` / `Gate` fields from a `tasks.md`.
**Where**: `scripts/_tasksmd.py`
**Depends on**: None
**Reuses**: Regex conventions from `tlc-spec-driven/scripts/validate_tasks.py` (`TASK_RE`, field patterns).
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `parse(path)` returns tasks in document order, each carrying id, phase number, depends-on list, tests, and gate
- [x] Phase membership is derived from the `### Phase N` headings
- [x] A `tasks.md` with no tasks returns an empty list rather than raising
- [x] Field parsing tolerates the bold-marker variations `validate_tasks.py` already accepts
- [x] Unit tests cover: a multi-phase file, an empty file, and a task missing an optional field

**Tests**: unit
**Gate**: quick

---

### T7: Pack phases into task-budgeted batches ✅

**What**: Implement the batching algorithm - accumulate whole phases in order until the task budget is reached, never splitting a phase.
**Where**: `scripts/_batching.py`
**Depends on**: T6
**Reuses**: Algorithm specified in `tlc-spec-driven/references/sub-agents.md`.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `pack(tasks, budget)` returns batches of consecutive whole phases, never splitting a phase
- [x] A trailing batch of one or two tasks is folded into the previous batch
- [x] The worked examples from `sub-agents.md` reproduce exactly: `[3,3,3,3,4,4]` yields three batches, `[8,2,2,8]` yields three, `[5,5,5,5]` yields two
- [x] A phase exceeding roughly 1.5x the budget is returned flagged, not silently split
- [x] Unit tests cover all three worked examples plus the oversized-phase flag

**Tests**: unit
**Gate**: quick

---

### T8: Phase detection entrypoint ✅

**What**: The read-only CLI that prints exactly one phase line derived from git, `tasks.md`, and state.
**Where**: `scripts/detect_phase.py`
**Depends on**: T5, T7
**Reuses**: `_gitio`, `_tasksmd`, `_batching`, `_state_io`, and `tlc-spec-driven/scripts/validate_state.py` for the terminal check.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Exactly one line is printed per invocation, from the documented vocabulary
- [x] Absent `loop.json` prints `phase=0 action=bootstrap`
- [x] Completed tasks come from git trailers unioned with `no_diff_tasks`, and git wins over any conflicting state
- [x] Pending tasks remaining prints `phase=B` with the packed batch and explicit task IDs
- [x] No pending tasks and no PASS report prints `phase=V`, or `phase=F` when the last verdict was FAIL with gaps open
- [x] `validate_state.py` exiting 0 prints `phase=E`
- [x] A met halt condition prints `phase=H` with a reason slug, checked before any work is described
- [x] The script performs no writes: a run leaves `git status --porcelain` and `loop.json` byte-identical
- [x] Unit tests cover every output variant and assert the no-write property

**Tests**: unit
**Gate**: quick

---

### T9: Document the detect contract ✅

**What**: Reference specifying the output vocabulary, entry conditions, and exit rules of `detect_phase.py`.
**Where**: `references/phase-transitions.md`
**Depends on**: T8
**Reuses**: Adapted from `cy-loop-tasks/references/phase-transitions.md`.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Every line the implementation can print is listed with its entry condition
- [x] The derivation order is documented, including that git wins over state
- [x] Exit rules per phase are stated, including that `phase=H` is checked first
- [x] No output variant is documented that T8 does not implement

**Tests**: none
**Gate**: build

---

### T10: State mutation entrypoint ✅

**What**: The only mutator of `loop.json` after bootstrap, including the runaway counters.
**Where**: `scripts/update_loop.py`
**Depends on**: None
**Reuses**: `_state_io`.
**Requirement**: LOOP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `--iteration-done` increments `iteration` exactly once per invocation
- [x] `iterations[]` is append-only and capped at the last 50 entries
- [x] A write targeting `objective` is rejected with a non-zero exit
- [x] `--task-done`, `--gate-attempt`, and `--verify-round` update the counters the halt conditions read
- [x] `iterations_without_commit` resets on a recorded commit and increments otherwise
- [x] Unit tests cover: the increment, the 50-entry cap, the immutable-objective rejection, and both counter transitions

**Tests**: unit
**Gate**: quick

---

### T11: Atomic checkpoint commit ✅

**What**: Create the per-task commit carrying `Task:` and `Gate:` trailers, refusing when the gate did not pass.
**Where**: `scripts/checkpoint.py`
**Depends on**: None
**Reuses**: `_gitio` for trailer composition; `tlc-spec-driven/scripts/check_commit.py` for message validation.
**Requirement**: LOOP-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A commit is created only when the caller asserts a passing gate; anything else exits non-zero without committing
- [x] The message is validated with `check_commit.py` before staging, and a non-zero exit aborts
- [x] The commit carries `Task: <id>` and `Gate: <level> PASS` trailers, readable back with `%(trailers:key=Task,valueonly)`
- [x] A task with no file changes prints `SKIP: no changes` and exits 0 without an empty commit
- [x] `--no-verify` appears nowhere in the implementation
- [x] Unit tests build a tmpdir repo and cover: successful commit with trailers read back, refusal without a passing gate, refusal on an invalid message, and the no-changes path

> A trailer the message already carries is kept rather than repeated, and one
> contradicting the flags is refused. Appending unconditionally put two `Task:`
> trailers on every commit, which `_gitio.completed_tasks` reads as the rebase
> ambiguity from spec.md's edge cases.

**Tests**: unit
**Gate**: quick

---

### T12: Bootstrap entrypoint

**What**: Validate preconditions, detect the harness, and write the initial `loop.json` exactly once.
**Where**: `scripts/init_loop.py`
**Depends on**: None
**Reuses**: `_paths`, `_config`, `_state_io`, `_gitio`; `tlc-spec-driven/scripts/validate_tasks.py`.
**Requirement**: LOOP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Each precondition failure exits non-zero naming which one failed: not a git repo, missing `tasks.md`, `validate_tasks.py` non-zero, unparseable config
- [ ] Harness detection resolves from environment markers and records the result in `harness_resolved`
- [ ] Inconclusive detection with no explicit `respawn.provider` exits non-zero asking rather than guessing
- [ ] `objective` is written verbatim from the invocation and never derived
- [ ] Re-running against an existing `loop.json` refuses rather than overwriting
- [ ] Unit tests cover every precondition failure, successful bootstrap, inconclusive detection, and the re-run refusal

**Tests**: unit
**Gate**: quick

---

### T13: Document the state schema

**What**: Reference specifying every `loop.json` field, its meaning, and the single-writer invariants.
**Where**: `references/state-schema.md`
**Depends on**: T10, T12
**Reuses**: Adapted from `cy-loop-tasks/references/state-schema.md`.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Every field written by T10 or T12 is documented with type and meaning
- [ ] The invariants are stated: single writer, append-only capped log, immutable objective, no stored current phase
- [ ] It is stated explicitly that completed tasks are absent by design and derived from git
- [ ] No field is documented that the implementation does not write

**Tests**: none
**Gate**: build

---

### T14: Probe provider environment markers and effort values

**What**: Run the discovery inside `codex` and `cursor-agent` to capture their real environment markers and accepted effort values.
**Where**: `references/provider-discovery.md`
**Depends on**: None
**Reuses**: Method already used for Claude Code (`CLAUDECODE=1`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_EFFORT`).
**Requirement**: LOOP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Environment markers that uniquely identify `codex` and `cursor-agent` are captured verbatim from a run inside each
- [ ] Accepted `effort` values are confirmed per provider, replacing the `[?]` entries in the design's table
- [ ] Every captured value records how it was obtained, so a future reader can re-verify
- [ ] Any provider whose marker could not be determined is recorded as unresolved rather than guessed

**Tests**: none
**Gate**: build

---

### T15: Provider adapter table

**What**: Reference table translating `provider` / `model` / `effort` into a concrete command line per provider.
**Where**: `references/providers.md`
**Depends on**: T14
**Reuses**: Invocations verified during design: `codex exec -m X -c model_reasoning_effort=Y -o FILE`, `cursor-agent -p --force --model X`, `claude -p --model X`.
**Requirement**: LOOP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Each provider has its invocation template, effort mechanism, and evidence-capture mechanism
- [ ] Accepted effort values per provider come from T14, with unverified entries marked as such
- [ ] It is stated that `ultra` is accepted by no provider
- [ ] The rule that a provider equal to the running harness uses the native sub-agent path is documented

**Tests**: none
**Gate**: build

---

### T16: Stage resolution entrypoint

**What**: Turn a configured stage into a concrete invocation, rejecting unsupported effort before dispatch.
**Where**: `scripts/resolve_stage.py`
**Depends on**: T15
**Reuses**: `_config`, `_paths`; the adapter table from T15.
**Requirement**: LOOP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `--stage <name>` prints either `kind=agent` with model and effort, or `kind=command` with the full command line
- [ ] A provider equal to the detected running harness resolves to `kind=agent`
- [ ] An effort value the target provider does not accept exits non-zero naming the stage, the provider, and the accepted values
- [ ] `--validate` checks every configured stage and exits non-zero listing all offenders at once
- [ ] Placeholders for repo path and evidence file are substituted, never left literal
- [ ] Unit tests cover: each provider's command line, the native-agent path, a rejected effort, and `--validate` with multiple offenders

**Tests**: unit
**Gate**: quick

---

### T17: Executor dispatch contract

**What**: Reference specifying the worker payload format, the evidence contract, and the two universal executor rules.
**Where**: `references/executors.md`
**Depends on**: T16
**Reuses**: Generalised from `cy-loop-tasks/references/herdr-delegation.md`.
**Requirement**: LOOP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The payload contents are specified for a batch worker, a verifier, and a fix implementer
- [ ] The rule that an executor never commits is stated, with the reason
- [ ] The rule that evidence is verified and never trusted is stated, with what counts as evidence per provider
- [ ] The timeout behaviour is documented, including that a timeout counts as an executor failure
- [ ] Using `herdr` is shown as one ordinary `command` executor, not a special case

**Tests**: none
**Gate**: build

---

### T18: Recovery loop reference

**What**: The self-healing repair procedure and the three-criteria external-blocker test.
**Where**: `references/recovery-loop.md`
**Depends on**: None
**Reuses**: Ported nearly whole from `cy-loop-tasks/references/recovery-loop.md`, which is already stack-agnostic.
**Requirement**: LOOP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The repair loop steps are stated, including that a blind rerun is not a repair
- [ ] The normative failure-classification table is adapted to this project's gates
- [ ] All three external-blocker criteria are stated, with what explicitly does not qualify
- [ ] The prohibition on weakening, deleting, or skipping tests to pass a gate is stated
- [ ] Compozy-specific rows are replaced, not carried over

**Tests**: none
**Gate**: build

---

### T19: Portable shell driver

**What**: The restart driver for harnesses without a native goal mechanism.
**Where**: `scripts/loop.sh`
**Depends on**: None
**Reuses**: `detect_phase.py` output contract; `resolve_stage.py` for the respawn command.
**Requirement**: LOOP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The loop breaks on `phase=E` and on `phase=H`, printing the line it broke on
- [ ] Any other phase line spawns the resolved respawn command
- [ ] An unparseable detect line breaks the loop rather than spinning
- [ ] `bash -n` passes
- [ ] Integration tests drive it with a stubbed `detect_phase` and cover: terminate on E, terminate on H, one spawn then terminate, and the unparseable-line break

**Tests**: integration
**Gate**: full

---

### T20: Goal condition template

**What**: Ready-made `/goal` condition text anchored on the done-signature, for Claude Code and codex.
**Where**: `assets/goal-condition.template.md`
**Depends on**: None
**Reuses**: Documented `/goal` behaviour - the evaluator reads the conversation and cannot run commands.
**Requirement**: LOOP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The condition text references the literal done-signature line including the feature name
- [ ] The condition stays within the documented 4000-character limit
- [ ] It is stated why the condition anchors on printed output rather than on a script
- [ ] The codex native-goal equivalent is shown alongside

**Tests**: none
**Gate**: build

---

### T21: SKILL.md

**What**: The skill entrypoint: invocation, phase branches, critical rules.
**Where**: `SKILL.md`
**Depends on**: None
**Reuses**: Structure of `cy-loop-tasks/SKILL.md`; frontmatter conventions of `tlc-spec-driven/SKILL.md`.
**Requirement**: LOOP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Frontmatter carries a name and a description that triggers on loop-execution phrasing and excludes single-task work
- [ ] One branch per phase, each stating its done-when condition
- [ ] The continue gate is stated: re-enter detection in the same turn unless the phase is terminal or a halt condition holds
- [ ] The blast-radius rule is stated as halt-and-wait, not ask-and-proceed
- [ ] Every referenced script and reference file exists at the stated path

**Tests**: none
**Gate**: build

---

### T22: Per-iteration checklist

**What**: The self-audit checklist walked before printing each iteration summary.
**Where**: `references/checklist.md`
**Depends on**: T21
**Reuses**: Adapted from `cy-loop-tasks/references/checklist.md`.
**Requirement**: LOOP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] There is an every-iteration section plus one section per phase
- [ ] Each item is checkable against an artifact or a command result, never against recollection
- [ ] The author-is-not-verifier item appears in the verify section
- [ ] No item references a phase or script this skill does not have

**Tests**: none
**Gate**: build

---

### T23: Iteration summary template

**What**: The summary block printed after every completed iteration, including the done-signature line.
**Where**: `assets/iteration-summary.template.md`
**Depends on**: T21
**Reuses**: Adapted from `cy-loop-tasks/assets/iteration-summary.template.md`.
**Requirement**: LOOP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The block carries phase in and out, action, outcome, checkpoint result, halt reason, and next phase
- [ ] The done-signature is specified as the final line when the phase is terminal, carrying the feature name
- [ ] It is stated that intermediate failures do not render the block

**Tests**: none
**Gate**: build

---

### T24: Example configuration

**What**: A commented starter `loop.config.toml` a user can copy and edit.
**Where**: `assets/loop.config.example.toml`
**Depends on**: None
**Reuses**: The config shape from T3 and T4.
**Requirement**: LOOP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Every key from `references/config-schema.md` appears, commented with its default
- [ ] The example shows a cross-provider setup: a cheap implementer with a high-reasoning verifier
- [ ] `tomllib` parses the file without error
- [ ] The unlimited-by-omission rule is shown by example

**Tests**: none
**Gate**: build

---

### T25: Mutation-test the reused tlc validators

**What**: Confirm `validate_tasks.py`, `check_commit.py`, and `validate_state.py` actually reject invalid input, using the method that exposed the `validate_spec.py` false negative.
**Where**: `scripts/test_int_tlc_validators.py`
**Depends on**: None
**Reuses**: The three sibling validators via `_paths.tlc_script()`.
**Requirement**: LOOP-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Each validator is fed at least one deliberately invalid input and asserted to exit non-zero
- [ ] Each validator is fed a valid input and asserted to exit 0, so the test cannot pass by always failing
- [ ] Any validator found to pass vacuously is reported in the test failure message with the input that slipped through
- [ ] The tests skip cleanly with an explanatory message when the sibling skill is absent

**Tests**: integration
**Gate**: full

---

### T26: Loop-mode handoff in tlc-spec-driven

**What**: Extend the Execute delegation offer from two options to three, adding loop mode.
**Where**: `~/.agents/skills/tlc-spec-driven/references/implement.md`
**Depends on**: None
**Reuses**: The existing offer text in the sub-agent delegation step.
**Requirement**: LOOP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The offer presents inline, sub-agents, and loop mode, with one line on when each fits
- [ ] Loop mode names the invocation exactly
- [ ] Declining loop mode leaves the existing behaviour byte-for-byte unchanged
- [ ] No other section of `implement.md` is modified

**Tests**: none
**Gate**: build

---

### T27: End-to-end loop over a toy feature

**What**: Drive the whole loop across a fixture feature in a tmpdir git repo: bootstrap, two batches, checkpoint, resume after deleting state, terminal.
**Where**: `scripts/test_int_end_to_end.py`
**Depends on**: T25
**Reuses**: Every script built in phases 1 to 6.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A fixture repo with a valid `tasks.md` bootstraps, then `detect_phase` names the first batch
- [ ] Simulated task commits with trailers advance the detected phase without any state write
- [ ] Deleting `loop.json` mid-run still yields the same next task on the following detect
- [ ] A halt condition produces `phase=H` with the expected reason and the loop stops
- [ ] Executors are stubbed - the test spawns no real provider CLI and makes no network call

**Tests**: integration
**Gate**: full

---

### T28: Halt on corrupt state instead of exiting raw

**What**: Make `detect_phase.py` report an unparseable `loop.json` as `phase=H reason=state_corrupt` rather than a bare non-zero exit.
**Where**: `scripts/detect_phase.py`
**Depends on**: None
**Reuses**: The halt vocabulary already implemented for the other halt reasons.
**Requirement**: LOOP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] An unparseable `loop.json` prints `phase=H action=halt reason=state_corrupt` with the parse error as `detail`
- [ ] An absent `loop.json` still reconstructs from git and `tasks.md`, unchanged
- [ ] Every consumer of the detect contract sees one vocabulary: no caller needs to special-case a raw exit code
- [ ] `references/phase-transitions.md` documents `state_corrupt` alongside the other halt reasons
- [ ] Unit tests cover both branches: absent reconstructs, corrupt halts with the reason

**Tests**: unit
**Gate**: quick
