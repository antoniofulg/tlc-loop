# tlc-loop

An unattended execution loop for [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills).

`tlc-spec-driven` plans a feature and executes it — one batch at a time, stopping
at the end of every turn for you to prompt the next one. `tlc-loop` drives that
same execution to a verified PASS without the prompting: it derives what to do
next from git, repairs its own gate failures instead of stopping, halts for a
reason it writes down, and can run each stage on a different provider.

Adapted from [`cy-loop-tasks`](https://github.com/compozy/compozy/tree/main/.agents/skills/cy-loop-tasks)
(Compozy). Concepts ported, no code copied.

---

## Requirements

- Python 3.11+ (stdlib only — no packages to install)
- git
- [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills) installed **as a sibling directory**
- A project with a `tasks.md` that passes `validate_tasks.py`

## Install

The skill resolves its sibling with `realpath`, so it must physically sit beside
`tlc-spec-driven`. A symlink pointing out of the skills directory does not work —
the lookup follows the link and then fails to find the sibling next to the target.

```bash
git clone <this-repo> ~/.agents/skills/tlc-loop
ln -s ../../.agents/skills/tlc-loop ~/.claude/skills/tlc-loop
```

Verify:

```bash
python3 -c "
import importlib.util, os
p = os.path.expanduser('~/.agents/skills/tlc-loop/scripts/_paths.py')
s = importlib.util.spec_from_file_location('p', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
print(m.tlc_dir())"
```

It should print the path to `tlc-spec-driven`. Anything else means the two are
not siblings.

## Quick start

Plan a feature with `tlc-spec-driven` as usual. Once its `tasks.md` is approved:

```
/tlc-loop my-feature
```

That is the whole invocation. From there the loop bootstraps, works through the
batches, dispatches an independent verifier, and stops on a verified PASS or on
a recorded halt.

To see what it would do without doing anything:

```bash
python3 ~/.agents/skills/tlc-loop/scripts/detect_phase.py my-feature --root .
```

This is read-only. It prints exactly one line and writes nothing, so it is safe
to run at any point, including mid-run.

## Configuration

Optional. Absent, every key falls back to a documented default. Copy
`assets/loop.config.example.toml` to `.specs/loop.config.toml` in your project.

The setup this skill exists for — a cheap implementer paired with a
high-reasoning verifier:

```toml
[stages.implement]
provider = "codex"
model = "gpt-5.6-luna"
effort = "max"

[stages.verify]
provider = "claude"
model = "opus"
effort = "high"

[stages.fix]
provider = "codex"
model = "gpt-5.6-luna"
effort = "max"

[limits]                    # omit a key for unlimited
no_progress_iterations = 3
gate_attempts_per_task = 3
```

Check the whole file before a long run, so a bad stage surfaces now rather than
four hours in:

```bash
python3 ~/.agents/skills/tlc-loop/scripts/resolve_stage.py --validate --root . --feature my-feature
```

Supported providers: `claude`, `codex`, `cursor`. Each expresses model and effort
differently; the adapter table in `references/providers.md` holds the translation.
The file is user-owned — the loop reads it and never writes it.

## Running unattended across turns

The loop continues by itself within a turn. When the turn itself ends, something
has to start the next one:

| Harness | Mechanism |
| --- | --- |
| Claude Code | `/goal` — condition text ready to paste in `assets/goal-condition.template.md` |
| codex | its native goal feature |
| anything else | `bash scripts/loop.sh my-feature --root .` |

A goal evaluator reads the transcript; it cannot run commands. So the loop prints
a literal signature line once — and only once — `validate_state.py` exits 0:

```
__TLC_LOOP__ feature=my-feature verify=PASS
```

The supplied condition judges on that line alone. It explicitly rejects a summary
claiming the feature is finished, a green test run, and a passing report, which is
what stops a run from being declared done because the model said so.

## How it decides what to do next

Task completion lives in **git commit trailers**, not in a status field:

```
feat(auth): add token refresh service

Task: T3
Gate: quick PASS
```

`detect_phase.py` reads them with
`git log --format="%(trailers:key=Task,valueonly)"` and compares against
`tasks.md`. There is no stored "current phase" — it is re-derived every run.
Delete `.specs/features/my-feature/loop.json` mid-run and the next detect names
the same next task, because that file is a cache and git is the truth.

## When it stops

Every stop is recorded, never a silent stall.

| Reason | Meaning |
| --- | --- |
| `phase=E` | Verified PASS. The only successful terminal |
| `no_progress` | N iterations with no new commit — usually a bug, not slow work |
| `gate_stuck` | The same task's gate failed more times than the limit allows |
| `executor` | A provider CLI is missing, unauthenticated, or out of quota |
| `verify_exhausted` | Verify rounds spent without a PASS |
| `state_corrupt` | `loop.json` cannot be parsed |
| `limit` | A configured iteration or minute ceiling |
| `blocker` | A proven external blocker |
| `blast_radius` | A push, deploy, or destructive operation needs authorization |

The last one waits rather than asking. An unattended run has nobody to answer a
prompt, so a question and a hang are the same event; a recorded halt is resumable
the moment a human reads it.

## Known limitations

Stated plainly, because finding these yourself at 3am is worse.

- **The repair loop has never run in anger.** `references/recovery-loop.md` is
  instruction for the model, not code, and no real iteration has failed yet to
  exercise it. Start with a medium-sized feature.
- **codex is not auto-detected.** Its environment marker could not be determined
  (the account hit its usage limit during discovery, and the obvious candidate is
  unset under `danger-full-access` — exactly when detection would be needed).
  Name it explicitly with `--respawn codex`. Procedure to resolve this in
  `references/provider-discovery.md`.
- **A non-Claude provider needs a `command` executor**, which gets no shared
  context — the whole payload travels by file.
- **Eleven acceptance criteria are prose**, verified by review rather than by a
  test. The build gate proves those documents exist, not that they are correct.

## Development

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'      # full suite
python3 -m unittest discover -s scripts -p 'test_unit_*.py' # unit only
python3 -m compileall -q scripts/ && bash -n scripts/loop.sh
```

`.specs/` holds this skill's own planning record — spec, design, the decisions
behind it, and the validation report. It doubles as the integration fixture: the
loop can be pointed at this repository and will correctly name its own next task.

`SKILL.md` is the agent-facing contract and the source of truth for the workflow.
This README exists for people; it deliberately points there instead of restating it.

## License

CC-BY-4.0
