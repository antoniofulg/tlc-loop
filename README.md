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

### 1. Configure the implementation stages

A stage is a label your plan puts on a phase. This file is what gives the label
meaning: **which CLI runs that phase, on which model, at which reasoning tier.**
Custom stages must exist in `.specs/loop.config.toml` before Tasks are
validated, because the routing gate checks every declared stage against it.

```toml
[stages.foundation]
provider = "codex"
model = "gpt-5.6-luna"
effort = "medium"

[stages.backend]
provider = "codex"
model = "gpt-5.6-luna"
effort = "high"

[stages.frontend]
provider = "cursor"
model = "composer-2.5"

[stages.docs]
provider = "claude"
model = "haiku"

[execute]
strict_routing = true
```

Every stage takes the same three keys, and only the first has a default worth
relying on:

| Key | Default | What it selects |
| --- | --- | --- |
| `provider` | `"auto"` — the harness the loop is running inside | Which CLI executes the phase: `claude`, `codex`, `cursor`, or one you declare under `[providers.<name>]` |
| `model` | absent — the provider's own default | Passed through to that CLI verbatim |
| `effort` | absent — the provider's own default | Reasoning tier: `low`, `medium`, `high`, `xhigh`, `max` |

`frontend` and `docs` omit `effort` above on purpose: that is how you leave a
provider's own default in place.

One field, three translations. `claude` takes a separate `--effort` flag, `codex`
takes a `-c model_reasoning_effort=` config override, and `cursor` has no effort
flag at all — the tier is part of the model id, so the adapter uses its bracket
syntax. That is why `effort` is one portable field in your config instead of
three vendor-specific ones; the table doing the translating is
[`references/providers.md`](references/providers.md).

`implement`, `verify`, and `fix` exist without being declared. `verify`, `fix`,
and `continue.respawn` are reserved runtime roles — a Tasks phase cannot route
to them. Every other name is yours: `foundation`, `backend`, `frontend`, and
`docs` are examples, not a fixed vocabulary, and `mobile`, `infra`, or `data`
work identically.

Stages are one of eight tables the file accepts — [Configuration](#configuration)
lists the whole surface, every key is specified in
[`references/config-schema.md`](references/config-schema.md), and
[`assets/loop.config.example.toml`](assets/loop.config.example.toml) is a
commented file to copy.

### 2. Ask for loop-compatible Tasks

Name both skills while `tlc-spec-driven` is authoring Tasks. Naming `$tlc-loop`
here contributes the output contract and nothing else: it does not take over the
phase and does not start Execute.

```text
$tlc-spec-driven create the tasks for feature <name> for execution by
$tlc-loop, with phases separated by stage.
```

To suggest the common domains without requiring them, append:

```text
Prioritize foundation, backend, frontend, and docs as configured in
.specs/loop.config.toml.
```

A filled-in request, for a feature with a real shape. Naming the dependencies
you already know about is what keeps the split from being decided by domain
labels alone:

```text
$tlc-spec-driven create the tasks for feature checkout-v2 for execution by
$tlc-loop. Separate phases by stage, prioritizing foundation, backend,
frontend, and docs as configured in .specs/loop.config.toml. Keep dependency
order ahead of domain boundaries: the payment client and its fixtures come
before any endpoint that calls it, and the checkout UI comes after the
endpoints it consumes.
```

This applies the [Tasks routing contract](references/tasks-routing-contract.md)
but does not start Execute. `tlc-spec-driven` still owns dependencies,
granularity, tests, review, and approval.

Each generated phase must put `Stage` on its first non-empty line:

```markdown
### Phase 2: Checkout API

**Stage:** backend
```

#### What the divided `tasks.md` looks like

The request above produces a phase list of this shape — headings and stages
only, tasks elided:

```markdown
### Phase 1: Payment client and fixtures

**Stage:** foundation

### Phase 2: Checkout and payment endpoints

**Stage:** backend

### Phase 3: Checkout UI

**Stage:** frontend

### Phase 4: Webhook reconciliation

**Stage:** backend

### Phase 5: Integration guide and runbook

**Stage:** docs
```

At execution time that becomes one batch per phase, each dispatched to whatever
its stage names in the config from step 1:

| Phase | Stage | Executor it resolves to |
| --- | --- | --- |
| 1 | `foundation` | `codex`, `gpt-5.6-luna`, effort `medium` |
| 2 | `backend` | `codex`, `gpt-5.6-luna`, effort `high` |
| 3 | `frontend` | `cursor`, `composer-2.5` |
| 4 | `backend` | `codex`, `gpt-5.6-luna`, effort `high` |
| 5 | `docs` | `claude`, `haiku` |

`backend` appearing twice is valid — a stage may reappear in later,
non-consecutive phases — and phase 4 stays where it is because the
reconciliation depends on the endpoints from phase 2. Batches are never mixed: a
stage change closes the current batch even when the task budget still has room.

#### Rules that decide the split

Applied in this order:

1. **Preserve dependency order.** It outranks every domain boundary.
2. **One effective stage per phase.** Tasks needing different stages never share
   a phase.
3. A stage may reappear in later, non-consecutive phases.
4. Target about seven tasks per phase, with a ceiling around ten.
5. Do not split a cohesive, testable task merely to obtain a prettier domain
   boundary.

A task that genuinely spans domains and cannot be divided uses the stage capable
of the whole task, usually `implement`. If its parts can ship and be tested
independently, split the task first and let each part take its own stage.

#### Shapes that are rejected

None of these fall back to a default; each one fails the routing gate:

```markdown
### Phase 1: API
Some explanation first.
**Stage:** backend
```

`Stage` has to be the first non-empty line after the heading. These values fail
too: `Backend` (not lowercase), `backend_api` (not kebab-case, which is
`[a-z][a-z0-9-]*`), `backned` (not a configured stage), and `verify` or `fix`
(reserved runtime roles). Phase numbers must be positive integers and unique, so
`Phase 2a` and a repeated `Phase 2` are errors, as is a second `Stage` in one
phase.

### 3. Validate before approval

Run both read-only gates:

```bash
python3 ~/.agents/skills/tlc-spec-driven/scripts/validate_tasks.py my-feature --root .
python3 ~/.agents/skills/tlc-loop/scripts/validate_routing.py my-feature --root .
```

The routing gate prints the effective map:

```text
route:
  Phase 1: Shared setup -> foundation
  Phase 2: Checkout API -> backend
  Phase 3: Checkout UI -> frontend
  Phase 4: Guides -> docs
```

Both commands must exit 0 before `tasks.md` is approved. An explicit typo,
unknown stage, duplicate/misplaced `Stage`, non-integer phase number, or
reserved runtime stage is an error; it never silently falls back.

At execution time, `detect_phase.py` makes the route authoritative on its
single output line:

```text
phase=B action=execute_batch batch=P2 tasks=T4,T5,T6 stage=backend
```

The loop passes that exact value to the resolver. To inspect the resolved
executor manually:

```bash
python3 ~/.agents/skills/tlc-loop/scripts/resolve_stage.py \
  --stage backend --root . --feature my-feature \
  --prompt "inspect only" --evidence /tmp/tlc-loop-evidence.txt
```

Do not derive the stage again from a phase title. Batches are homogeneous: a
stage change always closes the current batch.

### 4. Approve and run

Once `tasks.md` is approved:

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

### Compatibility and strict mode

| Setting | Phase without `**Stage:**` | Invalid explicit stage |
| --- | --- | --- |
| `strict_routing = false` (default) | Routes to `implement` | Rejected |
| `strict_routing = true` | Rejected | Rejected |

Leave strict mode off for existing `tasks.md` files. Turn it on when every
implementation phase must declare its operational route explicitly.

## Configuration

Optional for legacy `tasks.md`; required when phases use custom stage names.
Absent, every key falls back to a documented default. Copy
`assets/loop.config.example.toml` to `.specs/loop.config.toml` in your project.

Everything the file accepts, with the default each key falls back to. What a key
*means* is in [`references/config-schema.md`](references/config-schema.md); this
table is only the surface, so you can see what exists without opening it:

| Table | Keys | Default |
| --- | --- | --- |
| `version` | — | `1` |
| `[stages.<name>]` | `provider`, `model`, `effort` | `auto`, absent, absent |
| `[execute]` | `batch_size`, `strict_routing` | `7`, `false` |
| `[verify]` | `max_rounds` | unlimited |
| `[continue]` | `mode` | `auto` |
| `[continue.respawn]` | `provider`, `model`, `effort` | `auto`, absent, absent |
| `[limits]` | `no_progress_iterations`, `gate_attempts_per_task`, `executor_timeout_seconds`, `max_iterations`, `max_minutes` | unlimited |
| `[providers.<name>]` | `kind`, `command` | absent |

Under `[limits]`, absent means unlimited — TOML has no `null`, so a ceiling
applies only when written down. Before an unattended run set at least
`no_progress_iterations`, `gate_attempts_per_task`, and
`executor_timeout_seconds`: the first two catch a loop going nowhere, the third
catches a provider CLI that hangs and prints nothing at all.

The setup this skill exists for — a cheap implementer paired with a
high-reasoning verifier:

```toml
[stages.implement]
provider = "codex"
model = "gpt-5.6-luna"
effort = "max"

[stages.foundation]
provider = "codex"
model = "gpt-5.6-luna"
effort = "medium"

[stages.backend]
provider = "codex"
model = "gpt-5.6-luna"
effort = "high"

[stages.frontend]
provider = "cursor"
model = "composer-2.5"

[stages.docs]
provider = "claude"
model = "haiku"

[stages.verify]
provider = "claude"
model = "opus"
effort = "high"

[stages.fix]
provider = "codex"
model = "gpt-5.6-luna"
effort = "max"

[execute]
strict_routing = false       # missing Stage -> implement

[limits]                    # omit a key for unlimited
no_progress_iterations = 3
gate_attempts_per_task = 3
```

This block is the same stage set as `assets/loop.config.example.toml`, and a test
holds the two in sync. `frontend` and `docs` carry no `effort`, which leaves each
provider's own default in place.

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

A goal evaluator reads the transcript; it cannot run commands. So one script —
`finish_loop.py`, and nothing else in the skill — prints a literal signature line:

```
__TLC_LOOP__ feature=my-feature verify=PASS
```

The supplied condition judges on that line alone. It explicitly rejects a summary
claiming the feature is finished, a green test run, and a passing report, which is
what stops a run from being declared done because the model said so.

`finish_loop.py` prints it only after re-deriving that the detector says
`phase=E action=done`, the working tree is clean, and the recorded verdict still
covers HEAD — then recording completion and checking all three again. Matching
the line is therefore matching a deterministic check rather than a sentence.

## Verification freshness

A PASS describes the tree the verifier read. Anything committed afterwards is
code no verifier has seen, however green the gates, so the verdict is recorded
together with the commit it covered and stops counting the moment HEAD moves
past it.

That leaves one problem: committing `validation.md` moves HEAD too, so the
evidence could never be versioned without invalidating what it is evidence of.
The **seal** is the one commit that resolves it — a direct child of the verified
commit whose diff is exactly the report, carrying `Verification-Of` and
`Verification-Result` trailers, refusing runtime code, config, tests, `tasks.md`
and `design.md` alike:

```bash
python3 ~/.agents/skills/tlc-loop/scripts/checkpoint.py my-feature --root . --seal
```

For a change that must land after a PASS anyway — a base branch that moved —
`--reopen` does the opposite: it commits through the same authorized writer and
*voids* the verdict, so the next detect opens a fresh verification epoch and
asks for a new independent look at the merged tree.

`verify.max_rounds` bounds one such epoch, not the life of the run. A FAIL, fix,
re-verify cycle spends from it; a commit landing after a PASS starts a new epoch
with a full budget, because that tree has been verified zero times.

Before publishing, the read-only preflight answers whether HEAD is safe to push:

```bash
python3 ~/.agents/skills/tlc-loop/scripts/finish_loop.py my-feature --root . \
  --preflight origin/main
```

Full contract: `references/verification-freshness.md`.

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
Delete `.specs/features/my-feature/loop.json` mid-run and no task is stranded:
the next detect prints `phase=0 action=bootstrap`, and once you re-bootstrap it
names the same task it would have, because task progress lives in git. Nothing
else in the file does. You re-supply the objective, every limit budget restarts,
a recorded halt is cleared, and verification is owed again. It is a deliberate
act with a price, not a reset button.

## When it stops

Every stop is recorded, never a silent stall.

| Reason | Meaning |
| --- | --- |
| `phase=E` | Verified PASS. The only successful terminal |
| `no_progress` | N iterations with no new commit — usually a bug, not slow work |
| `gate_stuck` | The same task's gate failed more times than the limit allows |
| `executor` | A provider CLI is missing, unauthenticated, out of quota, or was killed for outliving its configured timeout |
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

- **A dispatched provider CLI runs with its approval prompts turned off.** The
  loop passes `--dangerously-skip-permissions` to claude,
  `--dangerously-bypass-approvals-and-sandbox` to codex (which also disables
  its sandbox), and `--force` to cursor — always, on every invocation. It has
  to: nobody is there to answer a prompt, so an executor that asks just hangs
  until morning. The consequence is real, so it is stated rather than buried:
  an executor can write any file it can reach and run any command, with no
  confirmation step. Run the loop where that blast radius is acceptable — your
  own worktree, a container, a throwaway machine — and not on a box you would
  mind losing. A push, deploy, or other remote operation is a separate matter
  and still halts for authorization rather than proceeding.
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
- **Thirteen acceptance criteria are prose**, verified by review rather than by a
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
