# STATE

## Decisions

_No project-level decisions recorded yet. Design has not promoted any to project
scope; feature-level decisions live in
`.specs/features/tlc-loop-tasks/context.md` (D1..D13)._

## Handoff

- **Feature**: tlc-loop-tasks (`.specs/features/tlc-loop-tasks/`)
- **Phase / Task**: Planning complete. Awaiting task approval before Execute.
- **Completed**: Discuss (13 decisions), Specify (7 stories, 38 EARS criteria, LOOP-01..07 — gate passes with criteria inspected), Design (architecture chosen, components, schemas, adapter table, risks), Tasks (27 tasks across 7 phases — `validate_tasks.py` 0 errors).
- **In-progress** (file:line): none
- **Next step**: User approves `tasks.md`, then choose the Execute mode (inline / phase-batch sub-agents / loop). 27 tasks pack into 4 batches: T1-T9, T10-T17, T18-T24, T25-T27.
- **Blockers**: none
- **Uncommitted files**: `.specs/` (untracked — no commit yet)
- **Branch**: main (no commits)

### Side work done this session

Fixed a false-negative in `~/.claude/skills/tlc-spec-driven/scripts/validate_spec.py`:
a blank line between the `**Acceptance Criteria**:` header and the first numbered
item closed the parser's AC block, so every spec written from the skill's own
template passed the acceptance-criteria gate without any criterion being checked.
Blank lines are now skipped; the block closes on a heading, a bold line, or `---`.
Verified A/B against a spec carrying a deliberately non-testable criterion: old
code exited 0, fixed code exits 1 and names the line. T25 mutation-tests the
remaining three validators for the same class of defect.

### Verified during planning

- git trailers: `git commit --trailer` writes, `%(trailers:key=Task,valueonly)` reads back only real entries, `check_commit.py` accepts the message (git 2.50.1)
- `tomllib` is stdlib on Python 3.14.6 — removed a hand-written YAML reader plus emitter from the design (D13)
- CLI flags for `codex exec`, `cursor-agent`, and `claude -p`; `codex` has no `--effort` or `--agent` flag, effort goes through `-c model_reasoning_effort=`
- Claude Code `/goal` exists and is documented; its evaluator reads the transcript and cannot run commands, which is why the done-signature exists
- `pytest`, `ruff`, and `shellcheck` are not installed — tests use stdlib `unittest`

### Open verification debts

1. Environment markers for `codex` and `cursor-agent` — owned by T14.
2. Whether `cursor-agent` has any native continuation mechanism — probed in T14.
3. Exact `/goal` condition text against the real evaluator — owned by T20.
4. That the `no_diff_tasks` union produces no false positive after a rebase — owned by T11 and T27.
