"""Unit tests for init_loop.py (T12, LOOP-06).

Derived from T12's "Done when" criteria and:
  - LOOP-06 AC 3: the continuation mode is resolved from the running harness
    and the resolved value is recorded in `loop.json`
  - LOOP-06 AC 4: inconclusive harness detection halts and asks rather than
    guessing a continuation mechanism
  - LOOP-06 AC 5: the objective recorded at bootstrap is immutable afterwards,
    so it must be written verbatim from the invocation (D12)
  - spec.md edge cases: not a git repository, and a `tasks.md` that is missing
    or fails `validate_tasks.py`, both refuse to start the loop

The environment is built explicitly for every run rather than inherited: the
suite itself executes inside a harness, so an inherited marker would silently
decide the detection tests.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))

# Honours validate_tasks.py's contract abstractly: it is a gate that can fail.
# The real validator is mutation tested in T25.
VALIDATE_TASKS_STUB = '''#!/usr/bin/env python3
import os, sys
target = sys.argv[1]
root = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else "."
path = target if os.path.isfile(target) else os.path.join(
    root, ".specs", "features", target, "tasks.md")
if not os.path.isfile(path):
    print(f"validate_tasks: no such file {path}", file=sys.stderr)
    sys.exit(1)
text = open(path, encoding="utf-8").read()
if "INVALID" in text:
    print("validate_tasks: FAIL - granularity smell", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
'''

TASKS_MD = "# demo Tasks\n\n### T1: One\n**Tests**: unit\n**Gate**: quick\n"
OBJECTIVE = "ship demo end to end"


def _git(root, *args):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc


class InitLoopCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = self.tmp.name

        self.skill_scripts = os.path.join(base, "skills", "tlc-loop", "scripts")
        os.makedirs(self.skill_scripts)
        for name in os.listdir(SCRIPTS):
            if name.endswith(".py") and not name.startswith("test_"):
                shutil.copyfile(
                    os.path.join(SCRIPTS, name), os.path.join(self.skill_scripts, name)
                )

        tlc_scripts = os.path.join(base, "skills", "tlc-spec-driven", "scripts")
        os.makedirs(tlc_scripts)
        with open(os.path.join(tlc_scripts, "validate_tasks.py"), "w", encoding="utf-8") as fh:
            fh.write(VALIDATE_TASKS_STUB)

        self.root = os.path.join(base, "project")
        self.feature_dir = os.path.join(self.root, ".specs", "features", "demo")
        os.makedirs(self.feature_dir)
        self.write_tasks(TASKS_MD)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "loop@test.invalid")
        _git(self.root, "config", "user.name", "Loop Test")

    # ---- fixture helpers -------------------------------------------------

    def write_tasks(self, text):
        with open(os.path.join(self.feature_dir, "tasks.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def write_config(self, text):
        specs = os.path.join(self.root, ".specs")
        os.makedirs(specs, exist_ok=True)
        with open(os.path.join(specs, "loop.config.toml"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def state_path(self):
        return os.path.join(self.feature_dir, "loop.json")

    def state(self):
        with open(self.state_path(), encoding="utf-8") as fh:
            return json.load(fh)

    def run_init(self, *args, harness="claude", root=None, objective=OBJECTIVE):
        """Run bootstrap with an environment built from scratch."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k in ("PATH", "HOME", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR")
        }
        if harness == "claude":
            env["CLAUDECODE"] = "1"
        elif harness == "cursor":
            env["CURSOR_AGENT"] = "1"
        elif harness == "both":
            env["CLAUDECODE"] = "1"
            env["CURSOR_AGENT"] = "1"
        # harness=None leaves no marker at all: detection must be inconclusive
        return subprocess.run(
            [
                sys.executable,
                os.path.join(self.skill_scripts, "init_loop.py"),
                "demo",
                "--root", self.root if root is None else root,
                "--objective", objective,
                *args,
            ],
            capture_output=True,
            text=True,
            env=env,
        )


class Preconditions(InitLoopCase):
    """Each failure exits non-zero naming which precondition failed."""

    def test_a_project_that_is_not_a_git_repository_is_refused(self):
        outside = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(os.path.join(outside, ".specs", "features", "demo"))
        with open(os.path.join(outside, ".specs", "features", "demo", "tasks.md"), "w") as fh:
            fh.write(TASKS_MD)
        proc = self.run_init(root=outside)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("git", proc.stderr.lower())

    def test_a_missing_tasks_md_is_refused_and_named(self):
        os.remove(os.path.join(self.feature_dir, "tasks.md"))
        proc = self.run_init()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("tasks.md", proc.stderr)

    def test_a_tasks_md_failing_its_validator_is_refused_and_named(self):
        self.write_tasks(TASKS_MD + "\nINVALID\n")
        proc = self.run_init()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("validate_tasks", proc.stderr)

    def test_an_unparseable_config_is_refused_and_named(self):
        self.write_config("this is not = = toml")
        proc = self.run_init()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("loop.config.toml", proc.stderr)

    def test_no_state_file_is_written_when_a_precondition_fails(self):
        self.write_tasks(TASKS_MD + "\nINVALID\n")
        self.run_init()
        self.assertFalse(os.path.exists(self.state_path()))


class ConfigIsUnderstoodBeforeTheRunStarts(InitLoopCase):
    """T39: `version` and `continue.mode` are checked here, or nowhere.

    Both keys parse fine and mean nothing to the loop unless something compares
    them. A future schema version would be half-honoured and a typo'd mode would
    pick the wrong way to restart a turn - neither is visible until the run has
    been idle for hours, which is exactly the failure bootstrap exists to catch.
    """

    def test_an_unsupported_schema_version_is_refused(self):
        self.write_config("version = 2\n")
        proc = self.run_init()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("version", proc.stderr)
        self.assertFalse(os.path.exists(self.state_path()))

    def test_the_refusal_names_the_versions_it_understands(self):
        self.write_config("version = 99\n")
        self.assertIn("supported: 1", self.run_init().stderr)

    def test_the_supported_version_bootstraps(self):
        self.write_config("version = 1\n")
        self.assertEqual(self.run_init().returncode, 0)

    def test_an_unknown_continue_mode_is_refused(self):
        self.write_config('[continue]\nmode = "shel"\n')
        proc = self.run_init()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("continue.mode", proc.stderr)
        self.assertFalse(os.path.exists(self.state_path()))

    def test_the_refusal_lists_the_accepted_modes(self):
        self.write_config('[continue]\nmode = "shel"\n')
        stderr = self.run_init().stderr
        for accepted in ("auto", "goal", "shell", "none"):
            self.assertIn(accepted, stderr)

    def test_every_documented_mode_bootstraps(self):
        for mode in ("auto", "goal", "shell", "none"):
            with self.subTest(mode=mode):
                self.setUp()
                self.write_config(f'[continue]\nmode = "{mode}"\n')
                self.assertEqual(self.run_init().returncode, 0, mode)

    def test_a_limit_that_could_never_fire_is_refused(self):
        self.write_config("[limits]\nexecutor_timeout_seconds = 0\n")
        proc = self.run_init()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("executor_timeout_seconds", proc.stderr)


class SuccessfulBootstrap(InitLoopCase):
    def test_it_exits_zero_and_writes_the_state_file(self):
        proc = self.run_init()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.isfile(self.state_path()))

    def test_the_documented_initial_shape_is_written(self):
        self.run_init()
        state = self.state()
        self.assertEqual(state["feature"], "demo")
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["iteration"], 0)

    def test_completed_tasks_is_absent_by_design(self):
        self.run_init()
        self.assertNotIn("completed_tasks", self.state())

    def test_an_absent_config_bootstraps_on_defaults(self):
        self.assertEqual(self.run_init().returncode, 0)


class ObjectiveIsVerbatim(InitLoopCase):
    """LOOP-06 AC 5 / D12: written exactly as given, never derived."""

    def test_the_objective_is_stored_exactly_as_passed(self):
        self.run_init()
        self.assertEqual(self.state()["objective"], OBJECTIVE)

    def test_punctuation_and_spacing_survive_unchanged(self):
        odd = "  Ship  auth-refresh: phase 2 (P1) -- don't derive this!  "
        self.run_init(objective=odd)
        self.assertEqual(self.state()["objective"], odd)

    def test_the_objective_is_not_replaced_by_the_feature_name(self):
        self.run_init()
        self.assertNotEqual(self.state()["objective"], "demo")


class HarnessDetection(InitLoopCase):
    """LOOP-06 AC 3: resolved from environment markers, recorded in state."""

    def test_the_claude_marker_resolves_to_claude(self):
        self.run_init(harness="claude")
        self.assertEqual(self.state()["harness_resolved"], "claude")

    def test_the_cursor_marker_resolves_to_cursor(self):
        self.run_init(harness="cursor")
        self.assertEqual(self.state()["harness_resolved"], "cursor")


class InconclusiveDetection(InitLoopCase):
    """LOOP-06 AC 4: ask, never guess."""

    def test_no_marker_at_all_exits_non_zero(self):
        proc = self.run_init(harness=None)
        self.assertNotEqual(proc.returncode, 0)

    def test_the_refusal_tells_the_user_how_to_resolve_it(self):
        proc = self.run_init(harness=None)
        self.assertIn("--respawn", proc.stderr)

    def test_no_state_file_is_written_when_detection_is_inconclusive(self):
        self.run_init(harness=None)
        self.assertFalse(os.path.exists(self.state_path()))

    def test_two_harness_markers_at_once_are_inconclusive_rather_than_guessed(self):
        proc = self.run_init(harness="both")
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(os.path.exists(self.state_path()))

    def test_an_explicit_respawn_provider_resolves_an_undetectable_harness(self):
        proc = self.run_init("--respawn", "codex", harness=None)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.state()["harness_resolved"], "codex")

    def test_an_explicit_respawn_provider_wins_over_a_detected_marker(self):
        self.run_init("--respawn", "codex", harness="claude")
        self.assertEqual(self.state()["harness_resolved"], "codex")

    def test_a_configured_respawn_provider_resolves_an_undetectable_harness(self):
        self.write_config('[continue.respawn]\nprovider = "codex"\n')
        proc = self.run_init(harness=None)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.state()["harness_resolved"], "codex")

    def test_a_configured_provider_of_auto_still_requires_detection(self):
        self.write_config('[continue.respawn]\nprovider = "auto"\n')
        self.assertNotEqual(self.run_init(harness=None).returncode, 0)


class RerunRefusal(InitLoopCase):
    """Bootstrap happens exactly once; the objective is not silently replaced."""

    def test_a_second_run_exits_non_zero(self):
        self.assertEqual(self.run_init().returncode, 0)
        self.assertNotEqual(self.run_init().returncode, 0)

    def test_the_existing_state_is_left_byte_identical(self):
        self.run_init()
        with open(self.state_path(), "rb") as fh:
            before = fh.read()
        self.run_init(objective="a completely different objective")
        with open(self.state_path(), "rb") as fh:
            self.assertEqual(fh.read(), before)


if __name__ == "__main__":
    unittest.main()
