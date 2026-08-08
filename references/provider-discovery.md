# Provider discovery: environment markers and effort values

How the loop knows which harness it is running inside, and which reasoning
tiers each provider will accept. Everything here was captured on
**2026-08-08** against the CLIs installed on this machine.

A wrong marker is worse than a missing one. A missing marker makes detection
inconclusive, and `init_loop.py` then halts and asks (LOOP-06 AC 4). A wrong
marker silently misroutes every dispatch for the whole run. So nothing in this
file is inferred from a plausible naming convention: each value records how it
was obtained, and anything that could not be established is marked
**UNRESOLVED** rather than guessed.

---

## Evidence classes

Findings are graded, because they are not equally trustworthy.

| Class | What it means | Trust |
| --- | --- | --- |
| **A - live probe** | Captured from `env` running *inside* a session of that CLI | Highest. This is what the loop will actually see. |
| **B - CLI self-report** | Printed by the CLI itself (`--help`, `--list-models`) | High for flags and model names, silent about environment. |
| **C - binary inspection** | String literals in the shipped executable | Suggestive only. Shows a name exists; does not show it is exported to a child process. |
| **UNRESOLVED** | Could not be established | Not used. Detection declines instead. |

Only class A is accepted as an environment marker in
`init_loop.HARNESS_MARKERS`.

---

## Contamination: harnesses nest

A probe run from inside another agent inherits that agent's environment. The
cursor probe below was launched from a Claude Code session, and its output
contained `AI_AGENT=claude-code_2-1-224_agent` and several `ORCA_*` variables.
Those are the **parent's**, not cursor's.

Every marker below was cross-checked against the launching shell's own
environment and kept only if it was absent there. `CURSOR_*` and `CODEX_*` were
confirmed absent from the parent:

```bash
env | sort | grep -iE "cursor|codex|openai|claude|agent"
# -> CLAUDE* and AI_AGENT/ORCA_* only; no CURSOR_*, no CODEX_*
```

This is also why `AI_AGENT` is unusable as a discriminator: it was set by
Claude Code and leaked into a child that was not Claude Code.

It is why `detect_harness()` treats *two* matching harnesses as inconclusive.
Nesting is real, and nothing in the environment says which harness is
innermost.

---

## `claude` - Claude Code

**Markers: class A.** Read directly from the environment of this session.

| Variable | Example value | Notes |
| --- | --- | --- |
| `CLAUDECODE` | `1` | Primary marker. |
| `CLAUDE_CODE_ENTRYPOINT` | `cli` | Also distinguishes the entrypoint. |
| `CLAUDE_EFFORT` | `xhigh` | The session's current effort tier. |
| `CLAUDE_CODE_SESSION_ID` | *(uuid)* | Per-session, not usable as a stable marker. |

```bash
env | sort | grep -iE "^claude"
```

**Effort: class B.** `claude --help` exposes effort as its own flag, separate
from the model:

```
--effort <level>    Effort level for the current session
--model <model>     Model for the current session
```

Accepted values `low, medium, high, xhigh, max`. `xhigh` is confirmed in use
(`CLAUDE_EFFORT=xhigh` in this session).

---

## `cursor` - cursor-agent

**Markers: class A.** Captured by running the probe inside a real
`cursor-agent` session:

```bash
cursor-agent -p --force --output-format text \
  'Run exactly this shell command and paste its complete raw output verbatim
   into your final message, then stop: env | sort | grep -iE "cursor|agent|composer"'
```

Verbatim, with session identifiers redacted:

| Variable | Example value | Notes |
| --- | --- | --- |
| `CURSOR_AGENT` | `1` | Primary marker. |
| `CURSOR_INVOKED_AS` | `cursor-agent` | Corroborates, and names the entrypoint. |
| `CURSOR_CONVERSATION_ID` | *(uuid)* | Per-session. |
| `CURSOR_RIPGREP_PATH` | `~/.local/share/cursor-agent/versions/<ver>/rg` | Carries the version. |
| `AGENT_TRANSCRIPTS` | `~/.cursor/projects/<slug>/agent-transcripts` | Generic name; prefer `CURSOR_AGENT`. |
| `__CURSOR_SANDBOX_ENV_RESTORE` | *(shell snippet)* | Sandbox bookkeeping. |

The loop uses `CURSOR_AGENT` and `CURSOR_INVOKED_AS`.

**Effort: class B**, from `cursor-agent --list-models`. Cursor has no
`--effort` flag. Effort is **baked into the model id as a suffix**, or passed
with bracket syntax, which `--help` documents:

```
--model 'claude-opus-4-8[context=1m,effort=high,fast=false]'
```

Suffixes observed across the catalogue:

| Suffix | Example model id |
| --- | --- |
| `-low` | `claude-opus-5-low`, `gpt-5.6-luna-low` |
| `-medium` | `claude-opus-5-medium`, `gpt-5.6-terra-medium` |
| `-high` | `claude-sonnet-5-high`, `gpt-5.6-sol-high` |
| `-xhigh` | `claude-opus-5-thinking-xhigh`, `gpt-5.4-xhigh` |
| `-max` | `claude-opus-5-thinking-max`, `gpt-5.6-luna-max` |
| `-none` | `gpt-5.6-sol-none`, `gpt-5.5-none` |
| `-minimal` | `gemini-3.6-flash-minimal` |

So `low, medium, high, xhigh, max` are all confirmed for cursor. This corrects
the design's table, which listed `max` as unverified.

**The suffix set is per-model, not global.** `gpt-5.5` spells the tier
`gpt-5.5-extra-high`, not `-xhigh`, and `-fast` variants exist alongside most
tiers. A model id must be checked against `--list-models`; the loop cannot
synthesise one from an effort name alone.

---

## `codex` - UNRESOLVED

### Environment marker: UNRESOLVED

**No marker is recorded for codex, and `init_loop.HARNESS_MARKERS` has no
codex entry.** Running inside codex therefore yields inconclusive detection,
and the user names it explicitly:

```bash
init_loop.py <feature> --objective "..." --respawn codex
```

That is the designed fallback, not a defect. It is strictly safer than a
guessed marker.

#### What was tried

1. **Live probe (the class A route).**
   ```bash
   codex exec --skip-git-repo-check -o out.txt \
     'Run exactly this shell command and paste its complete raw output verbatim
      into your final message, then stop: env | sort | grep -iE "codex|openai|agent|sandbox"'
   ```
   The session started - `SessionStart` hooks fired - then:
   `ERROR: You've hit your usage limit. ... try again at Aug 9th, 2026 10:06 PM.`
   The model never ran a shell command, so no environment was captured.

2. **Hook route, to sidestep the model entirely.** Session hooks fire before
   the model call, so an isolated `CODEX_HOME` was built with a `SessionStart`
   hook running `env | sort > file`. The hook never fired: a fresh `CODEX_HOME`
   carries no `[hooks.state]` trust hashes, and the session additionally failed
   `401 Unauthorized` because credentials live in the real `CODEX_HOME`.
   Linking the real credentials into a temporary home was rejected as too
   invasive for a discovery task.

3. **Binary inspection (class C).** `strings` on the codex executable yields
   plausible names: `CODEX_SANDBOX`, `CODEX_SANDBOX_NETWORK_DISABLED`,
   `CODEX_THREAD_ID`, `CODEX_HOME`, `CODEX_NON_INTERACTIVE`, `CODEX_CI`.
   **None of these is adopted**, for two reasons. A string in the binary does
   not distinguish a variable codex *reads* from one it *exports* to a child -
   `CODEX_HOME` is clearly the former. And `CODEX_SANDBOX` would only be set
   when the sandbox is active; this machine runs
   `default_permissions = ":danger-full-access"`, so it would be absent
   precisely when detection is needed.

4. **Offline provider.** `codex exec --oss` needs a local backend; neither
   `ollama` nor LM Studio is installed.

#### How to resolve it later

Re-run attempt 1 once quota resets. If it succeeds, add the confirmed variable
to `init_loop.HARNESS_MARKERS` and change this section from UNRESOLVED to
class A. Nothing else needs to change: the explicit `--respawn codex` path
keeps working either way.

### Effort values: class C

| Accepted | Evidence |
| --- | --- |
| `minimal, low, medium, high, xhigh, max` | serde enum variant list in the binary: the literal `minimallowmediumhighxhighmax` |

Corroborating, from the same binary: the message templates
`` Reasoning effort ` `` and `` `. Supported reasoning efforts: ``, and the
config keys `model_reasoning_effort`, `plan_mode_reasoning_effort`,
`default_subagent_reasoning_effort`.

Independently, the user's own `~/.codex/config.toml` - a working configuration
- uses two of them:

```toml
model_reasoning_effort = "xhigh"
plan_mode_reasoning_effort = "xhigh"
default_subagent_reasoning_effort = "max"
```

This upgrades the design's `[?]` on codex `low, medium, high` to class C
evidence. It is **not** class A: no live run confirmed them end to end.

**The set is per-model and served remotely.** The binary carries API response
fields `supportedReasoningEfforts` and `defaultReasoningEffort` on its model
catalogue, so which tiers a given codex model accepts is decided by the
server, not by a fixed local list.

### Codex does not validate effort locally

Worth knowing, because it shapes where validation has to live. Every value
below, including a deliberately absurd one, got past local config parsing and
failed only at the API call:

```bash
codex exec --strict-config -c model_reasoning_effort=definitely_bogus_value 'hi'
# -> ERROR: You've hit your usage limit  (not a config error)
```

A bad effort is therefore **not** caught by codex before dispatch. This is why
`resolve_stage.py` rejects an unsupported effort itself, before spawning
anything (LOOP-05 AC 2).

---

## Summary

| Provider | Marker | Class | Effort values | Class |
| --- | --- | --- | --- | --- |
| `claude` | `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT` | A | `low, medium, high, xhigh, max` | B |
| `cursor` | `CURSOR_AGENT`, `CURSOR_INVOKED_AS` | A | `low, medium, high, xhigh, max` (suffix or bracket, per-model) | B |
| `codex` | **UNRESOLVED** - name with `--respawn codex` | - | `minimal, low, medium, high, xhigh, max` (per-model, server-decided) | C |

`ultra` appears nowhere, in any provider, by any evidence class.
