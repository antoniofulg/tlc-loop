"""Unit tests for resolve_stage.py (T16, LOOP-05).

Derived from T16's "Done when" criteria and:
  - LOOP-05 AC 1: provider, model and effort are resolved from
    `.specs/loop.config.toml` and translated through the provider adapter table
  - LOOP-05 AC 2: an effort the target provider does not accept is rejected
    before dispatch, not sent and left to fail silently
  - LOOP-05 AC 3: a provider equal to the running orchestrator uses the
    harness-native sub-agent mechanism instead of spawning a CLI

The command lines asserted here come from `references/providers.md`, which
records how each flag was verified against the installed CLI. The environment
is built explicitly for every run: the suite executes inside a harness, and an
inherited marker would otherwise decide the native-agent tests.
"""

import os
import shlex
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

import resolve_stage  # noqa: E402


class ResolveCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, ".specs"), exist_ok=True)

    def write_config(self, text):
        with open(os.path.join(self.root, ".specs", "loop.config.toml"), "w") as fh:
            fh.write(text)

    def run_resolve(self, *args, harness="none"):
        env = {
            k: v
            for k, v in os.environ.items()
            if k in ("PATH", "HOME", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR")
        }
        cmd = [sys.executable, os.path.join(SCRIPTS, "resolve_stage.py"), "--root", self.root]
        if harness != "none":
            cmd += ["--harness", harness]
        return subprocess.run([*cmd, *args], capture_output=True, text=True, env=env)

    def resolve_cmd(self, *args, harness="none"):
        proc = self.run_resolve(*args, harness=harness)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()


class CodexCommandLine(ResolveCase):
    def setUp(self):
        super().setUp()
        self.write_config(
            '[stages.implement]\nprovider = "codex"\n'
            'model = "gpt-5.6-luna"\neffort = "max"\n'
        )

    def test_it_resolves_to_a_command(self):
        line = self.resolve_cmd(
            "--stage", "implement", "--prompt", "do the work", "--evidence", "/tmp/e.txt"
        )
        self.assertTrue(line.startswith("kind=command provider=codex cmd="), line)

    def test_the_model_and_effort_use_the_verified_codex_flags(self):
        line = self.resolve_cmd(
            "--stage", "implement", "--prompt", "do the work", "--evidence", "/tmp/e.txt"
        )
        self.assertIn("codex exec -m gpt-5.6-luna", line)
        self.assertIn("-c model_reasoning_effort=max", line)

    def test_the_evidence_file_is_captured_with_output_last_message(self):
        line = self.resolve_cmd(
            "--stage", "implement", "--prompt", "do the work", "--evidence", "/tmp/e.txt"
        )
        self.assertIn("-o /tmp/e.txt", line)


class CursorCommandLine(ResolveCase):
    def test_effort_is_baked_into_the_model_with_bracket_syntax(self):
        self.write_config(
            '[stages.implement]\nprovider = "cursor"\n'
            'model = "claude-opus-5"\neffort = "high"\n'
        )
        line = self.resolve_cmd("--stage", "implement", "--prompt", "go")
        self.assertIn("claude-opus-5[effort=high]", line)

    def test_there_is_no_effort_flag(self):
        self.write_config(
            '[stages.implement]\nprovider = "cursor"\n'
            'model = "claude-opus-5"\neffort = "high"\n'
        )
        line = self.resolve_cmd("--stage", "implement", "--prompt", "go")
        self.assertNotIn("--effort", line)

    def test_the_non_interactive_flags_are_present(self):
        self.write_config('[stages.implement]\nprovider = "cursor"\nmodel = "composer-2.5"\n')
        line = self.resolve_cmd("--stage", "implement", "--prompt", "go")
        self.assertIn("cursor-agent -p go --force", line)
        self.assertIn("--output-format json", line)

    def test_a_model_that_already_carries_a_tier_plus_an_effort_is_refused(self):
        self.write_config(
            '[stages.implement]\nprovider = "cursor"\n'
            'model = "claude-opus-5-thinking-max"\neffort = "high"\n'
        )
        proc = self.run_resolve("--stage", "implement", "--prompt", "go")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("tier suffix", proc.stderr)


class ClaudeCommandLine(ResolveCase):
    def test_model_and_effort_are_separate_flags(self):
        self.write_config(
            '[stages.verify]\nprovider = "claude"\nmodel = "opus"\neffort = "high"\n'
        )
        line = self.resolve_cmd("--stage", "verify", "--prompt", "check it", harness="codex")
        self.assertIn("--model opus", line)
        self.assertIn("--effort high", line)

    def test_it_is_a_command_when_the_harness_is_something_else(self):
        self.write_config('[stages.verify]\nprovider = "claude"\nmodel = "opus"\n')
        line = self.resolve_cmd("--stage", "verify", "--prompt", "check it", harness="codex")
        self.assertIn("kind=command provider=claude", line)


class NativeAgentPath(ResolveCase):
    """LOOP-05 AC 3: the configured provider equals the running harness."""

    def test_a_provider_matching_the_harness_resolves_to_an_agent(self):
        self.write_config(
            '[stages.verify]\nprovider = "claude"\nmodel = "opus"\neffort = "high"\n'
        )
        line = self.resolve_cmd("--stage", "verify", harness="claude")
        self.assertEqual(line, "kind=agent provider=claude model=opus effort=high")

    def test_no_command_line_is_produced_for_the_native_path(self):
        self.write_config('[stages.verify]\nprovider = "claude"\nmodel = "opus"\n')
        line = self.resolve_cmd("--stage", "verify", harness="claude")
        self.assertNotIn("cmd=", line)

    def test_the_native_path_needs_no_prompt(self):
        self.write_config('[stages.verify]\nprovider = "claude"\n')
        self.assertEqual(self.run_resolve("--stage", "verify", harness="claude").returncode, 0)

    def test_provider_auto_resolves_to_the_running_harness(self):
        self.write_config('[stages.implement]\nprovider = "auto"\nmodel = "opus"\n')
        line = self.resolve_cmd("--stage", "implement", harness="claude")
        self.assertIn("kind=agent provider=claude", line)

    def test_the_harness_recorded_at_bootstrap_is_used_when_a_feature_is_named(self):
        import _state_io

        os.makedirs(os.path.join(self.root, ".specs", "features", "demo"))
        _state_io.save("demo", self.root, _state_io.new_state("demo", "obj", "cursor"))
        self.write_config('[stages.implement]\nprovider = "cursor"\nmodel = "composer-2.5"\n')
        proc = self.run_resolve("--stage", "implement", "--feature", "demo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("kind=agent provider=cursor", proc.stdout)

    def test_an_unresolvable_auto_provider_is_refused_rather_than_guessed(self):
        self.write_config('[stages.implement]\nprovider = "auto"\n')
        proc = self.run_resolve("--stage", "implement", "--prompt", "go")
        self.assertNotEqual(proc.returncode, 0)


class EffortRejection(unittest.TestCase):
    """LOOP-05 AC 2: reject before dispatch, naming stage, provider, accepted."""

    def test_an_effort_the_provider_does_not_accept_raises(self):
        with self.assertRaises(resolve_stage.ResolveError) as ctx:
            resolve_stage.check_effort("claude", "minimal", "implement")
        self.assertIn("implement", str(ctx.exception))
        self.assertIn("claude", str(ctx.exception))

    def test_the_error_lists_the_accepted_values(self):
        with self.assertRaises(resolve_stage.ResolveError) as ctx:
            resolve_stage.check_effort("cursor", "minimal", "fix")
        for value in ("low", "medium", "high", "xhigh", "max"):
            self.assertIn(value, str(ctx.exception))

    def test_an_accepted_effort_passes(self):
        self.assertIsNone(resolve_stage.check_effort("codex", "minimal", "implement"))
        self.assertIsNone(resolve_stage.check_effort("claude", "xhigh", "verify"))

    def test_ultra_is_accepted_by_no_provider(self):
        for provider in ("claude", "codex", "cursor"):
            with self.assertRaises(resolve_stage.ResolveError):
                resolve_stage.check_effort(provider, "ultra", "implement")


class ValidateEveryStage(ResolveCase):
    """`--validate` reports all offenders in one run."""

    def test_a_clean_config_validates(self):
        self.write_config(
            '[stages.implement]\nprovider = "codex"\nmodel = "m"\neffort = "max"\n'
            '[stages.verify]\nprovider = "claude"\nmodel = "opus"\neffort = "high"\n'
            '[stages.fix]\nprovider = "codex"\nmodel = "m"\neffort = "high"\n'
            '[continue.respawn]\nprovider = "claude"\nmodel = "opus"\n'
        )
        proc = self.run_resolve("--validate", harness="codex")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_it_exits_non_zero_when_a_stage_is_unusable(self):
        self.write_config('[stages.implement]\nprovider = "nosuchcli"\n')
        self.assertNotEqual(self.run_resolve("--validate", harness="codex").returncode, 0)

    def test_every_offender_is_listed_in_one_run(self):
        self.write_config(
            '[stages.implement]\nprovider = "nosuchcli"\n'
            '[stages.verify]\nprovider = "cursor"\n'
            'model = "gpt-5.6-luna-max"\neffort = "high"\n'
            '[stages.fix]\nprovider = "alsomissing"\n'
        )
        proc = self.run_resolve("--validate", harness="codex")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("nosuchcli", proc.stderr)
        self.assertIn("alsomissing", proc.stderr)
        self.assertIn("tier suffix", proc.stderr)

    def test_the_offender_count_is_reported(self):
        self.write_config(
            '[stages.implement]\nprovider = "nosuchcli"\n'
            '[stages.fix]\nprovider = "alsomissing"\n'
        )
        proc = self.run_resolve("--validate", harness="codex")
        self.assertIn("2 unusable stage(s)", proc.stderr)

    def test_validation_does_not_stop_at_the_first_offender(self):
        self.write_config(
            '[stages.aaa]\nprovider = "firstbad"\n[stages.zzz]\nprovider = "lastbad"\n'
        )
        proc = self.run_resolve("--validate", harness="codex")
        self.assertIn("firstbad", proc.stderr)
        self.assertIn("lastbad", proc.stderr)


class PlaceholderSubstitution(ResolveCase):
    """Placeholders are filled, never emitted literally."""

    def test_no_literal_placeholder_survives_in_a_resolved_command(self):
        self.write_config(
            '[stages.implement]\nprovider = "codex"\nmodel = "m"\neffort = "max"\n'
        )
        line = self.resolve_cmd(
            "--stage", "implement", "--prompt", "go", "--evidence", "/tmp/e.txt"
        )
        self.assertNotIn("{", line)

    def test_the_repo_path_is_substituted_with_the_real_root(self):
        self.write_config('[stages.implement]\nprovider = "codex"\nmodel = "m"\n')
        line = self.resolve_cmd(
            "--stage", "implement", "--prompt", "go", "--evidence", "/tmp/e.txt"
        )
        self.assertIn(f"-C {shlex.quote(os.path.abspath(self.root))}", line)

    def test_a_custom_template_has_its_placeholders_filled(self):
        self.write_config(
            '[stages.implement]\nprovider = "myagent"\nmodel = "m1"\n'
            '[providers.myagent]\nkind = "command"\n'
            'command = "myagent run --model {model} --out {evidence} --repo {repo}"\n'
        )
        line = self.resolve_cmd(
            "--stage", "implement", "--prompt", "go", "--evidence", "/tmp/e.txt"
        )
        self.assertIn("--model m1", line)
        self.assertIn("--out /tmp/e.txt", line)
        self.assertNotIn("{", line)

    def test_a_template_placeholder_with_no_value_is_refused(self):
        self.write_config(
            '[stages.implement]\nprovider = "myagent"\n'
            '[providers.myagent]\nkind = "command"\n'
            'command = "myagent run --out {evidence}"\n'
        )
        proc = self.run_resolve("--stage", "implement", "--prompt", "go")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("{evidence}", proc.stderr)

    def test_a_builtin_provider_missing_its_evidence_path_is_refused(self):
        self.write_config('[stages.implement]\nprovider = "codex"\nmodel = "m"\n')
        proc = self.run_resolve("--stage", "implement", "--prompt", "go")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("{evidence}", proc.stderr)


class Failures(ResolveCase):
    def test_an_unknown_stage_name_exits_non_zero(self):
        self.write_config('[stages.implement]\nprovider = "codex"\n')
        self.assertNotEqual(
            self.run_resolve("--stage", "nosuchstage", harness="codex").returncode, 0
        )

    def test_a_malformed_config_exits_non_zero(self):
        self.write_config("this is not = = toml")
        self.assertNotEqual(self.run_resolve("--stage", "implement").returncode, 0)

    def test_passing_neither_stage_nor_validate_is_refused(self):
        self.assertNotEqual(self.run_resolve().returncode, 0)

    def test_passing_both_stage_and_validate_is_refused(self):
        self.write_config('[stages.implement]\nprovider = "codex"\n')
        self.assertNotEqual(
            self.run_resolve("--stage", "implement", "--validate").returncode, 0
        )


if __name__ == "__main__":
    unittest.main()
