# Provider adapter table

How `provider` / `model` / `effort` from `.specs/loop.config.toml` become a
concrete thing to run. `scripts/resolve_stage.py` implements this table; this
file is its specification.

Nothing here is uniform across vendors, which is the whole reason the table
exists. Claude Code takes effort as its own flag, codex takes it as a config
override, and cursor bakes it into the model id. A single "effort" field in
the config only works because this layer translates it three different ways.

Marker and effort evidence comes from
[provider-discovery.md](provider-discovery.md), which grades every value by
how it was obtained. Evidence classes are carried through below.

---

## Two kinds of executor

| `kind` | Meaning |
| --- | --- |
| `agent` | Use the harness' own sub-agent mechanism. No process is spawned. |
| `command` | Spawn a CLI as a subprocess. |

### A provider equal to the running harness uses the native path

**When the configured provider for a stage equals the harness the loop is
running inside, the stage resolves to `kind=agent`** (LOOP-05 AC 3). The loop
dispatches through the harness' own sub-agent mechanism instead of spawning a
second CLI.

Running `claude -p` from inside Claude Code would start a fresh process with
its own authentication, its own context, and no access to the parent's
sub-agent tooling, to do work the harness can already delegate natively. It
also doubles the token cost of the same task.

The comparison is against `harness_resolved` in `loop.json` - the value
recorded at bootstrap - not a fresh detection. Detection happens once, so a
stage cannot resolve differently halfway through a run.

`provider = "auto"` means "the detected harness", so it always resolves to
`kind=agent`.

---

## Placeholders

Substituted into a command template at resolution. **A resolved command line
never contains a literal `{...}`**; an unsubstituted placeholder is a bug, not
a value to pass through.

| Placeholder | Replaced with |
| --- | --- |
| `{model}` | The stage's `model`. |
| `{effort}` | The stage's `effort`. |
| `{repo}` | Absolute path of the project root. |
| `{evidence}` | Absolute path of the file the executor must leave its result in. |
| `{prompt}` | The worker payload text. |

When a stage omits `model` or `effort`, the flag carrying it is dropped
entirely rather than passed empty, leaving the provider's own default in
place.

---

## `claude` - Claude Code

| | |
| --- | --- |
| **kind** | `agent` when the loop runs inside Claude Code, else `command` |
| **invocation** | `claude -p {prompt} --dangerously-skip-permissions --model {model} --effort {effort} --output-format stream-json` |
| **effort mechanism** | Separate `--effort <level>` flag |
| **approval bypass** | `--dangerously-skip-permissions`, always passed |
| **evidence capture** | stdout, `--output-format stream-json` |
| **accepted effort** | `low, medium, high, xhigh, max` - class B |

Effort and model are independent flags, so both are optional and either can be
dropped without affecting the other. Verified in `claude --help`:

```
--effort <level>                Effort level for the current session
--model <model>                 Model for the current session
--dangerously-skip-permissions  Bypass all permission checks.
--output-format <format>        Output format (only works with --print)
```

---

## `codex`

| | |
| --- | --- |
| **kind** | `command` |
| **invocation** | `codex exec --dangerously-bypass-approvals-and-sandbox -m {model} -c model_reasoning_effort={effort} -C {repo} -o {evidence} {prompt}` |
| **effort mechanism** | `-c model_reasoning_effort=<value>` config override |
| **approval bypass** | `--dangerously-bypass-approvals-and-sandbox`, always passed |
| **evidence capture** | `-o/--output-last-message <FILE>` |
| **accepted effort** | `minimal, low, medium, high, xhigh, max` - class C, per-model |

`-o` writes the agent's final message to a file, which is the cleanest evidence
channel of the three: it is a file the loop can check for existence and
content, not a stream it has to parse. `-C/--cd` sets the working root.

The bypass is passed by the loop, not left to the operator. Verified in
`codex exec --help`:

```
--dangerously-bypass-approvals-and-sandbox
    Skip all confirmation prompts and execute commands without sandboxing.
    EXTREMELY DANGEROUS.
```

`approval_policy = "never"` in `~/.codex/config.toml` produces the same
behaviour, and that is exactly the problem: it is a property of one machine.
A skill that depends on it works for whoever wrote it and hangs on an approval
prompt for everyone else, four hours into an unattended run.

Two cautions, both from discovery:

**Effort is not validated locally.** `codex exec -c
model_reasoning_effort=definitely_bogus_value` gets past config parsing and
fails only at the API. Codex will not catch a bad tier for us, so
`resolve_stage.py` must reject it before dispatch (LOOP-05 AC 2).

**The accepted set is per-model and decided server-side.** The codex model
catalogue carries `supportedReasoningEfforts` and `defaultReasoningEffort` per
model. The list above is the union the binary knows about; a specific model may
accept a subset.

---

## `cursor` - cursor-agent

| | |
| --- | --- |
| **kind** | `command` |
| **invocation** | `cursor-agent -p {prompt} --force --model {model} --output-format json` |
| **effort mechanism** | Baked into the model id, or bracket syntax on `--model` |
| **approval bypass** | `-f, --force`, always passed |
| **evidence capture** | stdout, `--output-format json` |
| **accepted effort** | `low, medium, high, xhigh, max` - class B, per-model |

Cursor has **no `--effort` flag**. Effort is part of the model identity:

```bash
cursor-agent -p --model claude-opus-5-thinking-xhigh          # suffix form
cursor-agent -p --model 'claude-opus-4-8[context=1m,effort=high,fast=false]'   # bracket form
```

The bracket form is documented in `cursor-agent --help` and is what the adapter
uses when a stage supplies `model` and `effort` separately, because appending a
suffix is not reliable: **suffixes are per-model**. `gpt-5.5` spells its tier
`gpt-5.5-extra-high`, not `-xhigh`, and `-fast` variants sit alongside most
tiers. Synthesising `{model}-{effort}` would produce ids that do not exist.

If a stage's `model` already carries a tier suffix, `effort` should be omitted;
specifying both is contradictory and the resolver rejects it rather than
guessing which wins.

Note `--force`: cursor-agent will not act non-interactively without it. See
the blast-radius warning below.

---

## Effort matrix

| effort | `claude` | `codex` | `cursor` |
| --- | --- | --- | --- |
| `minimal` | no | yes (C) | no |
| `low` | yes (B) | yes (C) | yes (B) |
| `medium` | yes (B) | yes (C) | yes (B) |
| `high` | yes (B) | yes (C) | yes (B) |
| `xhigh` | yes (B) | yes (C) | yes (B) |
| `max` | yes (B) | yes (C) | yes (B) |
| `ultra` | **no** | **no** | **no** |

Class B is a CLI self-report; class C is inferred from the shipped binary and
has not been confirmed by a live run. `minimal` is accepted by the loop's
config only if listed in `_config.EFFORTS`; it currently is not, so it is
unreachable through configuration even though codex would take it.

### `ultra` is accepted by no provider

It appears in no `--help`, no model catalogue, and no binary, for any of the
three. A stage configured with `effort = "ultra"` is rejected when the config
loads, with the offending stage named, so it never reaches dispatch.

---

## Custom providers

`[providers.<name>]` in `loop.config.toml` declares a CLI this table does not
cover, or overrides one it does:

```toml
[providers.myagent]
kind = "command"
command = "myagent run --model {model} --out {evidence}"
```

The same placeholder rules apply. A custom provider carries no effort
validation, because the loop has no catalogue for it: whatever `effort`
resolves to is substituted as given.

It carries no approval bypass either, for the same reason - the loop does not
know that CLI's flag. **Put it in the template yourself.** A custom provider
that stops to ask is a run that hangs until someone notices.

This is also the escape hatch for using `herdr`, or any other orchestrator, as
an executor. It is one ordinary `command` provider, not a special case.

---

## Blast radius

**Every built-in `command` executor is dispatched with its approval guardrail
switched off, by the loop, on every invocation.** Not by the operator's config,
not conditionally:

| Provider | Argument the loop passes |
| --- | --- |
| `claude` | `--dangerously-skip-permissions` |
| `codex` | `--dangerously-bypass-approvals-and-sandbox` |
| `cursor` | `--force` |

Read that as it is written. A dispatched executor can edit any file it can
reach, run any command, and delete anything, with nothing standing between it
and the machine. codex additionally runs unsandboxed. That is the deal
unattended execution makes: there is nobody at the keyboard at 3am, so a
prompt and a hang are the same event, and a run that asks is a run that stalls
silently until morning.

`resolve_stage.NON_INTERACTIVE` is where the arguments live, and every one of
them is pinned by a test, so a provider cannot be added without a deliberate
decision about this.

What the loop does *not* do is decide on its own that a dangerous operation is
fine. A blast-radius situation - a push, a deploy, a production data change -
**halts and waits** rather than asking or proceeding. The bypass buys
non-interactivity inside the local sandbox of a task; it is not authorization.

Run this on a machine, a container, or a worktree where that blast radius is
acceptable. If it is not, do not run the loop there.
