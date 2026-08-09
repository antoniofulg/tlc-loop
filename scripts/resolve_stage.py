#!/usr/bin/env python3
"""resolve_stage.py - turn a configured stage into something concrete to run.

`provider` / `model` / `effort` from `.specs/loop.config.toml` mean three
different things to three different CLIs: Claude Code takes effort as its own
flag, codex as a config override, cursor as part of the model id. This script
is the translation layer, specified by `references/providers.md`.

It resolves, it does not dispatch. Nothing here spawns a provider - which is
why `limits.executor_timeout_seconds` is *emitted* rather than applied. Whoever
spawns the process owns the clock: `loop.sh` for the respawn it starts itself,
and the agent for a stage it dispatches. The field rides the resolved line so
neither has to go read the config to find it.

Two rules it enforces before anything can be run:

* **A provider equal to the running harness resolves to `kind=agent`**
  (LOOP-05 AC 3). Spawning a second CLI to do work the harness can delegate
  natively costs a second authentication, a second context, and double the
  tokens.
* **A bad pairing is rejected here, not at the provider.** codex accepts
  `-c model_reasoning_effort=definitely_bogus_value` without complaint and
  fails only at the API, so the loop cannot rely on providers to catch their
  own bad input (LOOP-05 AC 2).

Usage:
    resolve_stage.py --stage implement [--feature F] [--root DIR]
                     [--prompt TEXT] [--evidence PATH] [--harness NAME]
    resolve_stage.py --validate [--root DIR] [--harness NAME]

Output, exactly one line:
    kind=agent provider=claude model=opus effort=high
    kind=command provider=codex cmd=<shell-quoted command line>

`timeout=<seconds>` is appended, before `cmd=`, whenever
`limits.executor_timeout_seconds` is set. An absent field means unlimited, the
same convention omission carries everywhere under `[limits]` (D8).

Exit codes: 0 resolved, 1 the config or state could not be read, 2 the
configuration is unusable (unknown provider, unsupported effort, unfilled
placeholder).
"""

import argparse
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _config  # noqa: E402
import _state_io  # noqa: E402
import init_loop  # noqa: E402

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

#: Effort values each built-in provider accepts, from references/providers.md.
#: `_config.EFFORTS` already limits configuration to the union of these, so
#: this table is the per-provider narrowing, not the first line of defence.
PROVIDER_EFFORTS = {
    "claude": ("low", "medium", "high", "xhigh", "max"),
    "codex": ("minimal", "low", "medium", "high", "xhigh", "max"),
    "cursor": ("low", "medium", "high", "xhigh", "max"),
}

#: Tier suffixes cursor bakes into a model id. A model already carrying one
#: plus an explicit effort is contradictory, and which wins is not guessable.
CURSOR_TIER_SUFFIXES = ("-low", "-medium", "-high", "-xhigh", "-max", "-extra-high")


class ResolveError(Exception):
    """The configuration cannot be turned into something runnable."""


def _claude_argv(model, effort, ctx):
    argv = ["claude", "-p", ctx["prompt"]]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    return argv + ["--output-format", "stream-json"]


def _codex_argv(model, effort, ctx):
    argv = ["codex", "exec"]
    if model:
        argv += ["-m", model]
    if effort:
        argv += ["-c", f"model_reasoning_effort={effort}"]
    return argv + ["-C", ctx["repo"], "-o", ctx["evidence"], ctx["prompt"]]


def _cursor_argv(model, effort, ctx):
    argv = ["cursor-agent", "-p", ctx["prompt"], "--force"]
    if model:
        # Bracket syntax, never `{model}-{effort}`: tier suffixes are
        # per-model, so a synthesised id is often one that does not exist.
        argv += ["--model", f"{model}[effort={effort}]" if effort else model]
    return argv + ["--output-format", "json"]


BUILTIN = {
    "claude": (_claude_argv, ("prompt",)),
    "codex": (_codex_argv, ("prompt", "repo", "evidence")),
    "cursor": (_cursor_argv, ("prompt", "repo")),
}


def check_effort(provider, effort, stage):
    """Raise when the provider does not accept this effort (LOOP-05 AC 2)."""
    if not effort or provider not in PROVIDER_EFFORTS:
        return
    accepted = PROVIDER_EFFORTS[provider]
    if effort not in accepted:
        raise ResolveError(
            f"stage {stage!r}: provider {provider!r} does not accept effort "
            f"{effort!r}; accepted values are {', '.join(accepted)}"
        )


def resolve_provider(stage, harness):
    """`auto` means the harness detected at bootstrap."""
    provider = stage.get("provider")
    if provider in (None, "", "auto"):
        return harness
    return provider


def resolve(name, stage, config, harness, ctx):
    """Resolve one stage. Returns a dict; raises ResolveError when unusable."""
    timeout = config["limits"]["executor_timeout_seconds"]
    provider = resolve_provider(stage, harness)
    if provider is None:
        raise ResolveError(
            f"stage {name!r}: provider is 'auto' but the running harness is "
            f"unknown; name it with continue.respawn.provider or --harness"
        )

    model, effort = stage.get("model"), stage.get("effort")
    check_effort(provider, effort, name)

    # The harness can delegate natively; no process is spawned. The timeout
    # still rides along: the agent owns the clock for a stage it dispatches.
    if provider == harness:
        return {"kind": "agent", "provider": provider, "model": model,
                "effort": effort, "timeout": timeout}

    custom = (config.get("providers") or {}).get(provider)
    if custom and custom.get("kind") == "agent":
        return {"kind": "agent", "provider": provider, "model": model,
                "effort": effort, "timeout": timeout}

    if custom and custom.get("command"):
        # `{model}` and `{effort}` are per-stage, so they join the context here
        # rather than being passed in by the caller.
        template_ctx = {**ctx, "model": model, "effort": effort}
        argv = _substitute(shlex.split(custom["command"]), template_ctx, name)
    elif provider in BUILTIN:
        builder, needed = BUILTIN[provider]
        missing = [key for key in needed if not ctx.get(key)]
        if missing:
            raise ResolveError(
                f"stage {name!r}: provider {provider!r} needs "
                f"{', '.join('{' + m + '}' for m in missing)} but no value was given"
            )
        if provider == "cursor" and effort and model:
            if model.endswith(CURSOR_TIER_SUFFIXES):
                raise ResolveError(
                    f"stage {name!r}: provider 'cursor' model {model!r} already "
                    f"carries a tier suffix and effort {effort!r} was also set; "
                    f"drop one - which wins is not guessable"
                )
        argv = builder(model, effort, ctx)
    else:
        raise ResolveError(
            f"stage {name!r}: unknown provider {provider!r}; known providers are "
            f"{', '.join(sorted(BUILTIN))}, or declare it under [providers.{provider}]"
        )

    return {
        "kind": "command",
        "provider": provider,
        "model": model,
        "effort": effort,
        "timeout": timeout,
        "argv": argv,
    }


def _substitute(tokens, ctx, name):
    """Fill placeholders in a custom template; a leftover one is an error."""
    out = []
    for token in tokens:
        filled = PLACEHOLDER_RE.sub(lambda m: str(ctx.get(m.group(1)) or m.group(0)), token)
        left = PLACEHOLDER_RE.findall(filled)
        if left:
            raise ResolveError(
                f"stage {name!r}: no value for placeholder(s) "
                f"{', '.join('{' + item + '}' for item in left)} in the command template"
            )
        out.append(filled)
    return out


def configured_stages(config):
    """Every stage the config declares, including the respawn agent."""
    stages = [(name, stage) for name, stage in sorted(config["stages"].items())]
    stages.append(("continue.respawn", config["continue"]["respawn"]))
    return stages


def known_harness(args, root):
    """`--harness` wins, then the value recorded at bootstrap, then detection."""
    if args.harness:
        return args.harness
    if args.feature:
        try:
            return _state_io.load(args.feature, root).get("harness_resolved")
        except _state_io.StateError:
            pass
    return init_loop.detect_harness()[0]


def _render(result):
    """One line. `timeout=` appears only when a limit is set (D8)."""
    fields = [f"kind={result['kind']}", f"provider={result['provider']}"]
    if result["kind"] == "agent":
        fields.append(f"model={result['model'] or '-'}")
        fields.append(f"effort={result['effort'] or '-'}")
    if result["timeout"] is not None:
        fields.append(f"timeout={result['timeout']}")
    if result["kind"] == "command":
        # Last, always: everything after ` cmd=` is the command line, which is
        # how `loop.sh` splits it back out.
        fields.append(f"cmd={shlex.join(result['argv'])}")
    return " ".join(fields)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="resolve_stage.py",
        description="Translate a configured stage into a concrete invocation.",
    )
    parser.add_argument("--stage", help="Stage to resolve, e.g. implement")
    parser.add_argument("--validate", action="store_true", help="Check every stage")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    parser.add_argument("--feature", help="Read the harness recorded at bootstrap")
    parser.add_argument("--harness", help="Name the running harness explicitly")
    parser.add_argument("--prompt", help="Payload text, substituted for {prompt}")
    parser.add_argument("--evidence", help="Evidence file, substituted for {evidence}")
    args = parser.parse_args(argv)

    if bool(args.stage) == bool(args.validate):
        parser.error("pass exactly one of --stage or --validate")

    root = os.path.abspath(args.root)
    try:
        config = _config.load_config(root)
    except _config.ConfigError as exc:
        print(f"resolve_stage: {exc}", file=sys.stderr)
        return 1

    harness = known_harness(args, root)
    ctx = {"repo": root, "prompt": args.prompt, "evidence": args.evidence}

    if args.validate:
        # Every offender at once: a run that fixes one and rediscovers the
        # next on the following invocation wastes a whole cycle each time.
        offenders = []
        for name, stage in configured_stages(config):
            try:
                resolve(name, stage, config, harness, {**ctx, "prompt": "x", "evidence": "x"})
            except ResolveError as exc:
                offenders.append(str(exc))
        for offender in offenders:
            print(f"resolve_stage: {offender}", file=sys.stderr)
        if offenders:
            print(f"resolve_stage: {len(offenders)} unusable stage(s)", file=sys.stderr)
            return 2
        print(f"ok {len(configured_stages(config))} stage(s) resolve")
        return 0

    stage = config["stages"].get(args.stage)
    if args.stage == "continue.respawn":
        stage = config["continue"]["respawn"]
    if stage is None:
        print(f"resolve_stage: no stage named {args.stage!r} in the config", file=sys.stderr)
        return 1

    try:
        result = resolve(args.stage, stage, config, harness, ctx)
    except ResolveError as exc:
        print(f"resolve_stage: {exc}", file=sys.stderr)
        return 2

    print(_render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
