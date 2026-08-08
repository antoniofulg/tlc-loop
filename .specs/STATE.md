# STATE

## Decisions

_No project-level decisions promoted to project scope. Feature-level decisions
live in `.specs/features/tlc-loop-tasks/context.md` (D1..D13)._

## Handoff

- **Feature**: tlc-loop-tasks (`.specs/features/tlc-loop-tasks/`)
- **Phase / Task**: Complete for the P1 group. `validate_state.py` exits 0.
- **Completed**: Discuss (13 decisions) · Specify (7 stories, 38 EARS criteria) · Design · Tasks (33) · Execute (32 tasks, 4 batches) · Validate (2 Verifier rounds, round 2 PASS)
- **In-progress** (file:line): none
- **Next step**: Two decisions await the user, both outside this repository — see Pending below. Nothing in this repo is blocked.
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: main, 34 commits, clean worktree

### Delivered

`SKILL.md` · 12 scripts under `scripts/` · 7 references · 3 assets · 321 tests.
Requirements LOOP-01 through LOOP-06 verified with `file:line` evidence.
LOOP-07 not delivered (task T26).

Task completion is recorded as git trailers, per D3. Read it back with:

```
git log --format="%(trailers:key=Task,valueonly)"
```

### Pending user decisions (both edit files outside this repo)

1. **T26 / LOOP-07** — extend the Execute delegation offer in
   `~/.agents/skills/tlc-spec-driven/references/implement.md` from two options
   (inline, sub-agents) to three (adding loop mode). Without it the loop works
   but is never suggested at the end of the Tasks phase.
2. **Two defects found in `tlc-spec-driven`, documented but not fixed.** Both
   affect every feature planned with that skill, not only this one:
   - `validate_tasks.py` attributes every task to the last `### Phase N`
     heading, so under the standard template its forward-dependency check
     cannot fail. Reproduced independently: a task in Phase 1 depending on a
     task in Phase 2 returns 0 errors.
   - The batching example in `sub-agents.md` does not reproduce under its own
     literal rule — `[8,2,2,8]` collapses to two batches, while the document
     claims three. `scripts/_batching.py` adds a 1.5x-budget guard to match the
     documented counts.

### Already fixed in `tlc-spec-driven` this session

`validate_spec.py` skipped every acceptance-criterion check when a blank line
sat between the `**Acceptance Criteria**:` header and the first item — which the
skill's own template produces. Every spec written from that template passed the
AC gate vacuously. Blank lines are now skipped; the block closes on a heading, a
bold line, or `---`. Verified A/B against a deliberately non-testable criterion.

### Verification debts carried forward

1. The `codex` environment marker is UNRESOLVED — the account hit its usage
   limit during T14. `codex` does not auto-detect and must be named with
   `--respawn`. Re-verification procedure in `references/provider-discovery.md`.
2. The `/goal` condition text in `assets/goal-condition.template.md` has not
   been exercised against the real evaluator.
3. 11 P1 criteria are agent-facing prose with no executable assertion, matching
   the approved Test Coverage Matrix. The build gate proves those documents
   exist, not that they are correct.

### Housekeeping

The checkout directory is `tlc-tasks-loop`; the skill is named `tlc-loop-tasks`
everywhere else. Rename the directory before symlinking it into
`~/.claude/skills/`.
