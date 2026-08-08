#!/usr/bin/env python3
"""init_loop.py - bootstrap a run: check preconditions, write `loop.json` once.

This is the only script that creates state. Everything after it either reads
state (`detect_phase.py`) or mutates it (`update_loop.py`), so every guarantee
the rest of the loop relies on has to be established here.

Preconditions, checked in this order and each naming itself on failure:

0. `loop.json` does not already exist - bootstrap happens once. Re-running
   refuses rather than overwriting, because overwriting would silently replace
   the immutable objective and reset the runaway counters.
1. The project is a git repository. Task status lives in commit trailers, so
   without a repository the loop has nowhere to record progress.
2. `.specs/features/<feature>/tasks.md` exists.
3. The sibling `validate_tasks.py` exits 0 on it. A plan that fails its own
   gate is not a plan the loop will execute unattended.
4. `.specs/loop.config.toml` parses. An absent file is fine - documented
   defaults apply - but a malformed one is not.
5. The running harness resolves, or a provider was named explicitly.

**Harness detection asks rather than guesses** (LOOP-06 AC 4). Only markers
verified by running inside the harness are listed in `HARNESS_MARKERS`; see
`references/provider-discovery.md` for how each was captured and which remain
unresolved. A harness with no verified marker simply does not detect, and the
user names it with `--respawn`. A wrong marker would silently misroute every
dispatch, so absence is the safe failure.

`objective` is written verbatim from the invocation and never derived. It is
immutable from here (D12).

Usage:
    init_loop.py <feature> --objective "<text>" [--root DIR] [--respawn PROVIDER]

Exit codes: 0 bootstrapped, 1 a precondition failed, 2 the request was refused
(already bootstrapped, or the harness could not be resolved).
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _config  # noqa: E402
import _gitio  # noqa: E402
import _paths  # noqa: E402
import _state_io  # noqa: E402

#: Environment markers that identify the harness a script is running inside.
#: Verified by probing each CLI; a harness whose marker could not be confirmed
#: is deliberately absent rather than guessed.
HARNESS_MARKERS = (
    ("claude", ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")),
    ("cursor", ("CURSOR_AGENT", "CURSOR_INVOKED_AS")),
)


def detect_harness(environ=None):
    """Return `(provider, detail)`; provider is None when inconclusive.

    More than one harness matching is inconclusive too. Harnesses nest - one
    can spawn another and its markers stay in the child's environment - and
    nothing in the environment says which one is innermost.
    """
    env = os.environ if environ is None else environ
    matched = [
        (name, [m for m in markers if env.get(m)])
        for name, markers in HARNESS_MARKERS
    ]
    matched = [(name, seen) for name, seen in matched if seen]

    if len(matched) == 1:
        name, seen = matched[0]
        return name, f"{', '.join(seen)} set in the environment"
    if not matched:
        known = ", ".join(m for _, markers in HARNESS_MARKERS for m in markers)
        return None, f"no known harness marker is set (looked for: {known})"
    names = ", ".join(name for name, _ in matched)
    return None, f"markers for more than one harness are set ({names}); cannot tell which is running"


def resolve_harness(args, config):
    """Explicit wins over configured, configured wins over detection (D10)."""
    if args.respawn:
        return args.respawn, "named by --respawn"
    configured = (config["continue"]["respawn"] or {}).get("provider")
    if configured and configured != "auto":
        return configured, "continue.respawn.provider in loop.config.toml"
    return detect_harness()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="init_loop.py",
        description="Bootstrap a loop run. Writes loop.json exactly once.",
    )
    parser.add_argument("feature")
    parser.add_argument("--objective", required=True, help="Recorded verbatim; immutable after")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    parser.add_argument("--respawn", metavar="PROVIDER", help="Name the harness instead of detecting it")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    # 0. Bootstrap is not idempotent by overwrite: it refuses.
    state_path = _state_io.state_path(args.feature, root)
    if os.path.exists(state_path):
        print(
            f"init_loop: {state_path} already exists; refusing to overwrite an "
            f"existing run (delete it deliberately to start over)",
            file=sys.stderr,
        )
        return 2

    # 1. A repository, because task status lives in commit trailers.
    if not _gitio.is_git_repo(root):
        print(
            f"init_loop: {root} is not a git repository; task status is recorded "
            f"as commit trailers, so the loop cannot run without one",
            file=sys.stderr,
        )
        return 1

    # 2. The plan exists.
    tasks_path = os.path.join(root, ".specs", "features", args.feature, "tasks.md")
    if not os.path.isfile(tasks_path):
        print(f"init_loop: no tasks.md at {tasks_path}", file=sys.stderr)
        return 1

    # 3. The plan passes its own gate.
    try:
        validator = _paths.tlc_script("validate_tasks.py")
    except _paths.SiblingSkillError as exc:
        print(f"init_loop: {exc}", file=sys.stderr)
        return 1
    checked = subprocess.run(
        [sys.executable, validator, args.feature, "--root", root],
        capture_output=True,
        text=True,
    )
    if checked.returncode != 0:
        sys.stderr.write(checked.stdout)
        sys.stderr.write(checked.stderr)
        print(
            f"init_loop: validate_tasks.py rejected {tasks_path}; fix the plan "
            f"before starting the loop",
            file=sys.stderr,
        )
        return 1

    # 4. The config parses, or is absent and defaults apply.
    try:
        config = _config.load_config(root)
    except _config.ConfigError as exc:
        print(f"init_loop: {exc}", file=sys.stderr)
        return 1

    # 5. The harness is known, or the user names it.
    harness, how = resolve_harness(args, config)
    if harness is None:
        print(
            f"init_loop: cannot tell which harness is running: {how}. "
            f"Re-run with --respawn <provider>, or set continue.respawn.provider "
            f"in .specs/loop.config.toml. Guessing would misroute every dispatch.",
            file=sys.stderr,
        )
        return 2

    state = _state_io.new_state(args.feature, args.objective, harness)
    try:
        _state_io.save(args.feature, root, state)
    except _state_io.StateError as exc:
        print(f"init_loop: {exc}", file=sys.stderr)
        return 1

    print(f"bootstrapped feature={args.feature} harness={harness} ({how})")
    print(f"state={state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
