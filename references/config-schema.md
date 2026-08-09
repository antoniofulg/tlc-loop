# `loop.config.toml` schema

The loop's only configuration file. It lives at `.specs/loop.config.toml`,
relative to the project root, and is parsed by `scripts/_config.py` with stdlib
`tomllib`.

**The file is optional.** When it is absent the loop runs on the defaults below.
Every key listed here is independently optional: an absent key resolves to its
default, so a config file that sets one value is valid.

---

## Two rules that shape the whole file

### Config is read-only to the loop

`loop.config.toml` is user-owned. The loop reads it and never writes it. No
script in this skill opens the file for writing, and no runtime value is
persisted back into it.

Runtime-resolved values go to `loop.json` instead. When `provider = "auto"`
resolves to a concrete harness at bootstrap, the resolved name is recorded in
`loop.json` as `harness_resolved`; the config still reads `auto`. That split is
what lets you edit the config between runs without fighting the loop for
ownership of the file, and what keeps your settings out of the state file that
one run throws away.

### TOML has no null, so omission means unlimited

TOML cannot express `null`. There is therefore no way to write "no limit" as a
value. The convention is the absence of the key:

**Under `[limits]`, an omitted key means unlimited.** A limit is enforced only
when you write it down. In the parsed config an unlimited limit is `None`.

`verify.max_rounds` is the one key outside `[limits]` that works the same way,
because it is the same kind of thing: a ceiling the user chooses, with no
hard-coded maximum behind it. Every other table has a real default value,
listed below.

---

## `version`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `version` | integer | `1` | Schema version of this file. |

```toml
version = 1
```

`1` is the only version this loop understands. `init_loop.py` refuses to
bootstrap against any other, so a config written for a different schema stops
the run before it starts rather than being half-honoured hours in.

---

## `[stages.*]`

`implement`, `verify`, and `fix` exist by default. Additional implementation
stages such as `foundation`, `backend`, `frontend`, or `docs` may be declared
with any lowercase kebab-case name. Each takes the same three keys and resolves
independently.

`verify`, `fix`, and `continue.respawn` are reserved runtime roles: a Tasks
phase cannot select them through `**Stage:**`. `implement` is the compatibility
fallback for a phase with no declaration when `execute.strict_routing` is
false. See [tasks-routing-contract.md](tasks-routing-contract.md).

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `provider` | string | `"auto"` | Which CLI or harness runs this stage. `"auto"` means the harness detected at bootstrap. |
| `model` | string | *(none)* | Model name, passed through to the provider adapter verbatim. Absent leaves the provider's own default in place. |
| `effort` | string | *(none)* | Reasoning tier. Absent leaves the provider's own default in place. |

`effort` accepts exactly: `low`, `medium`, `high`, `xhigh`, `max`.

Any other value is rejected when the config loads, with the offending stage
named, so a bad pairing never reaches dispatch. `ultra` is rejected: no
installed provider accepts it.

Loading validates only that the value is in the list above. Whether a *specific*
provider accepts a *specific* effort is a narrower question, checked at stage
resolution against the provider adapter table.

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

[stages.backend]
provider = "codex"
model = "gpt-5.6-luna"
effort = "high"

[stages.frontend]
provider = "cursor"
model = "composer-2.5"
```

---

## `[execute]`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `batch_size` | integer | `7` | Task budget per batch. Phases are packed into batches up to this many tasks, and a phase is never split across batches. |
| `strict_routing` | boolean | `false` | Require every Tasks phase to declare `**Stage:**`. When false, a missing declaration routes to `implement`; an invalid explicit declaration is always rejected. |

```toml
[execute]
batch_size = 7
strict_routing = false
```

A stage change closes the current batch even when the task budget has room.
The loop never mixes effective stages in one batch, and tail folding applies
only when both batches use the same stage.

---

## `[verify]`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `max_rounds` | integer | unlimited | How many verify rounds may run before the loop halts and escalates. |

`max_rounds` is not under `[limits]`, but it follows the same rule: omit it and
there is no ceiling. The verify budget is a user decision with no hard-coded
maximum, so the skill does not invent one.

Reaching the ceiling without a PASS makes `detect_phase.py` print
`phase=H action=halt reason=verify_exhausted` in place of the next `phase=V` or
`phase=F`. Set it if an unattended run should stop rather than keep paying for
verify rounds that are not converging.

```toml
[verify]
max_rounds = 3
```

---

## `[continue]`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | string | `"auto"` | How continuation is driven across turns: `auto`, `goal`, `shell`, or `none`. `auto` resolves from the running harness at bootstrap. |

`mode` is checked at bootstrap: a value outside those four is refused, because a
typo would silently pick the wrong way to restart a turn.

There is no key for continuing *within* a turn. LOOP-06 AC 1 requires the loop
to re-enter detection in the same turn while the phase is not terminal, so it
is not configurable. Use `mode = "none"` to stop the run from restarting a turn
once the current one ends.

### `[continue.respawn]`

The agent spawned to start the next turn. Same three keys as a stage, same
defaults, same `effort` validation.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `provider` | string | `"auto"` | Which CLI to respawn. `"auto"` is detected at bootstrap; an explicit value always wins. |
| `model` | string | *(none)* | Model for the respawned agent. |
| `effort` | string | *(none)* | Reasoning tier for the respawned agent. |

```toml
[continue]
mode = "auto"

[continue.respawn]
provider = "auto"
model = "opus"
effort = "high"
```

---

## `[limits]`

Every key here is unlimited when omitted. There are no numeric defaults in this
table.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `no_progress_iterations` | integer | *unlimited* | Halt after this many iterations with no new commit. |
| `gate_attempts_per_task` | integer | *unlimited* | Halt when one task's gate has failed more than this many times. |
| `executor_timeout_seconds` | integer | *unlimited* | Kill an executor invocation after this long. A timeout counts as an executor failure: it is recorded as `phase=H reason=executor`, never retried. Emitted by `resolve_stage.py` as `timeout=<seconds>` and enforced by whoever spawns the process - `loop.sh` for the respawn, the agent for a dispatched stage. |
| `max_iterations` | integer | *unlimited* | Halt cleanly once the run reaches this many iterations. |
| `max_minutes` | integer | *unlimited* | Halt cleanly once the run has been going this long. |

Every value must be a positive integer. `0` and a negative number are refused
at load rather than read as unlimited: omission already means unlimited, so a
zero is a typo, and a ceiling of zero would halt on the first iteration.

An unlimited run has no automatic stop. Before leaving a run unattended, set at
least `no_progress_iterations`, `gate_attempts_per_task`, and
`executor_timeout_seconds` - the first two catch a loop going nowhere, and the
third catches the one failure that produces no output at all: a provider CLI
that hangs.

```toml
[limits]
no_progress_iterations = 3
gate_attempts_per_task = 3
executor_timeout_seconds = 1800
# max_iterations = 200   # omitted -> unlimited
# max_minutes = 480      # omitted -> unlimited
```

---

## `[providers.*]`

Optional. Declares a CLI the built-in adapter table does not already cover, or
overrides the command line used for one it does.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `kind` | string | *(none)* | `command` for a CLI the loop spawns, `agent` for a harness-native sub-agent. |
| `command` | string | *(none)* | Command template. Placeholders are substituted at stage resolution. |

The config reader passes this table through unchanged and validates nothing
inside it. Stage resolution is what interprets `kind`, `command`, and the
placeholders. Absent, the table is empty and only the built-in providers are
available.

```toml
[providers.myagent]
kind = "command"
command = "myagent run --model {model} --out {evidence}"
```
