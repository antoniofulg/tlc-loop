"""Unit tests for _config - the loop.config.toml reader (T3, LOOP-05).

Derived from T3's "Done when" criteria plus:
  - spec.md edge case: "IF .specs/loop.config.toml is absent THEN the system
    SHALL run on documented defaults rather than failing"
  - spec.md assumption: valid effort values are low, medium, high, xhigh, max;
    `ultra` exists in no provider
  - LOOP-05 AC 2: an unsupported effort is rejected before dispatch
  - design.md D8: TOML has no null, so an omitted limit means unlimited
"""

import os
import tempfile
import unittest

import _config


def _write(root, text):
    specs = os.path.join(root, ".specs")
    os.makedirs(specs, exist_ok=True)
    path = os.path.join(specs, "loop.config.toml")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class AbsentFile(unittest.TestCase):
    def test_returns_a_fully_defaulted_config(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = _config.load_config(root)
            self.assertEqual(cfg["version"], 1)
            self.assertEqual(cfg["execute"]["batch_size"], 7)
            self.assertEqual(cfg["verify"]["max_rounds"], 3)
            self.assertIs(cfg["continue"]["in_turn"], True)
            self.assertEqual(cfg["continue"]["mode"], "auto")
            self.assertEqual(
                cfg["continue"]["respawn"],
                {"provider": "auto", "model": None, "effort": None},
            )
            self.assertEqual(cfg["providers"], {})
            for stage in ("implement", "verify", "fix"):
                self.assertEqual(
                    cfg["stages"][stage],
                    {"provider": "auto", "model": None, "effort": None},
                    stage,
                )

    def test_every_documented_key_is_present(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = _config.load_config(root)
            self.assertEqual(
                sorted(cfg),
                ["continue", "execute", "limits", "providers", "stages", "verify", "version"],
            )
            self.assertEqual(
                sorted(cfg["limits"]),
                [
                    "executor_timeout_seconds",
                    "gate_attempts_per_task",
                    "max_iterations",
                    "max_minutes",
                    "no_progress_iterations",
                ],
            )


class UnlimitedByOmission(unittest.TestCase):
    def test_absent_file_leaves_every_limit_unlimited(self):
        with tempfile.TemporaryDirectory() as root:
            limits = _config.load_config(root)["limits"]
            for key, value in limits.items():
                self.assertIsNone(value, key)

    def test_an_omitted_key_under_limits_resolves_to_unlimited(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "[limits]\nmax_iterations = 200\n")
            limits = _config.load_config(root)["limits"]
            self.assertEqual(limits["max_iterations"], 200)
            self.assertIsNone(limits["no_progress_iterations"])
            self.assertIsNone(limits["gate_attempts_per_task"])
            self.assertIsNone(limits["executor_timeout_seconds"])
            self.assertIsNone(limits["max_minutes"])


class PartialFile(unittest.TestCase):
    def test_configured_keys_win_and_absent_keys_keep_defaults(self):
        with tempfile.TemporaryDirectory() as root:
            _write(
                root,
                "[stages.implement]\n"
                'provider = "codex"\n'
                'model = "gpt-5.6-luna"\n'
                'effort = "max"\n'
                "\n"
                "[execute]\n"
                "batch_size = 5\n",
            )
            cfg = _config.load_config(root)
            self.assertEqual(
                cfg["stages"]["implement"],
                {"provider": "codex", "model": "gpt-5.6-luna", "effort": "max"},
            )
            self.assertEqual(cfg["execute"]["batch_size"], 5)
            # untouched tables keep their documented defaults
            self.assertEqual(
                cfg["stages"]["verify"],
                {"provider": "auto", "model": None, "effort": None},
            )
            self.assertEqual(cfg["verify"]["max_rounds"], 3)

    def test_a_partially_specified_stage_keeps_the_other_stage_defaults(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, '[stages.verify]\nprovider = "claude"\n')
            stage = _config.load_config(root)["stages"]["verify"]
            self.assertEqual(stage["provider"], "claude")
            self.assertIsNone(stage["model"])
            self.assertIsNone(stage["effort"])

    def test_an_extra_provider_table_is_returned(self):
        with tempfile.TemporaryDirectory() as root:
            _write(
                root,
                "[providers.myagent]\n"
                'kind = "command"\n'
                'command = "myagent run --model {model} --out {evidence}"\n',
            )
            providers = _config.load_config(root)["providers"]
            self.assertEqual(
                providers["myagent"],
                {"kind": "command", "command": "myagent run --model {model} --out {evidence}"},
            )


class MalformedFile(unittest.TestCase):
    def test_raises_with_the_parse_error_and_the_file_path(self):
        with tempfile.TemporaryDirectory() as root:
            path = _write(root, "[stages.implement\nprovider = codex\n")
            with self.assertRaises(_config.ConfigError) as ctx:
                _config.load_config(root)
            message = str(ctx.exception)
            self.assertIn(path, message)
            # the underlying tomllib parse error is surfaced, not swallowed
            self.assertRegex(message, r"line \d+|Expected|Invalid|closing")


class EffortValidation(unittest.TestCase):
    def test_rejects_an_unknown_effort_naming_the_offending_stage(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, '[stages.verify]\nprovider = "claude"\neffort = "ultra"\n')
            with self.assertRaises(_config.ConfigError) as ctx:
                _config.load_config(root)
            message = str(ctx.exception)
            self.assertIn("stages.verify", message)
            self.assertIn("ultra", message)

    def test_the_rejection_lists_the_accepted_values(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, '[stages.fix]\neffort = "turbo"\n')
            with self.assertRaises(_config.ConfigError) as ctx:
                _config.load_config(root)
            for accepted in ("low", "medium", "high", "xhigh", "max"):
                self.assertIn(accepted, str(ctx.exception))

    def test_accepts_every_valid_effort_value(self):
        for effort in ("low", "medium", "high", "xhigh", "max"):
            with tempfile.TemporaryDirectory() as root:
                _write(root, f'[stages.implement]\neffort = "{effort}"\n')
                self.assertEqual(
                    _config.load_config(root)["stages"]["implement"]["effort"], effort
                )

    def test_rejects_an_unknown_effort_on_the_respawn_stage(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, '[continue.respawn]\nprovider = "codex"\neffort = "ultra"\n')
            with self.assertRaises(_config.ConfigError) as ctx:
                _config.load_config(root)
            self.assertIn("continue.respawn", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
