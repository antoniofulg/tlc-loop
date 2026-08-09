#!/usr/bin/env python3
"""Validate and print the effective Stage route for every tasks.md phase."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import _config  # noqa: E402
import _routing  # noqa: E402
import _tasksmd  # noqa: E402


def _tasks_path(root, feature):
    return os.path.join(root, ".specs", "features", feature, "tasks.md")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate_routing.py",
        description="Validate phase Stage declarations without changing project state.",
    )
    parser.add_argument("feature")
    parser.add_argument("--root", default=".", help="Project root containing .specs/")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    tasks_path = _tasks_path(root, args.feature)
    if not os.path.isfile(tasks_path):
        print(f"validate_routing: no tasks.md at {tasks_path}", file=sys.stderr)
        return 1

    try:
        config = _config.load_config(root)
        phases = _tasksmd.parse_phases(tasks_path)
        routed = _routing.resolve(phases, config)
    except (_config.ConfigError, _tasksmd.TasksFormatError) as exc:
        print(f"validate_routing: {exc}", file=sys.stderr)
        return 1
    except _routing.RoutingError as exc:
        for error in exc.errors:
            print(f"validate_routing: {error}", file=sys.stderr)
        return 1

    print("route:")
    for phase in routed:
        print(
            f"  Phase {phase['number']}: {phase['title']} -> "
            f"{phase['effective_stage']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
