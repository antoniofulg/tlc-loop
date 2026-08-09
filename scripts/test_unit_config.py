"""Unit tests for _config - the loop.config.toml reader (T3, LOOP-05).

Derived from T3's "Done when" criteria plus:
  - spec.md edge case: "IF .specs/loop.config.toml is absent THEN the system
    SHALL run on documented defaults rather than failing"
  - spec.md assumption: valid effort values are low, medium, high, xhigh, max;
    `ultra` exists in no provider
  - LOOP-05 AC 2: an unsupported effort is rejected before dispatch
  - design.md D8: TOML has no null, so an omitted limit means unlimited
  - T39 / LOOP-06: every key the config defaults has a reader, and a `[limits]`
    value that is not a positive integer is rejected at load
"""

import os
import re
import tempfile
import unittest

import _config

SCRIPTS = os.path.dirname(os.path.abspath(__file__))


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
            self.assertIs(cfg["execute"]["strict_routing"], False)
            self.assertIsNone(cfg["verify"]["max_rounds"])
            self.assertEqual(cfg["continue"]["mode"], "auto")
            self.assertNotIn("in_turn", cfg["continue"])
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

    def test_an_omitted_max_rounds_is_unlimited_rather_than_a_hard_ceiling(self):
        # T29 / D5: the verify ceiling is configurable with no hard-coded
        # maximum, so an absent key imposes none.
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(_config.load_config(root)["verify"]["max_rounds"])

    def test_a_configured_max_rounds_is_read_verbatim(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "[verify]\nmax_rounds = 2\n")
            self.assertEqual(_config.load_config(root)["verify"]["max_rounds"], 2)


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
            self.assertIsNone(cfg["verify"]["max_rounds"])

    def test_strict_routing_reads_real_toml_booleans(self):
        for raw, expected in (("true", True), ("false", False)):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as root:
                _write(root, f"[execute]\nstrict_routing = {raw}\n")
                self.assertIs(_config.load_config(root)["execute"]["strict_routing"], expected)

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

    def test_strict_routing_rejects_non_boolean_values(self):
        for raw in ('"false"', "0", "1"):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as root:
                _write(root, f"[execute]\nstrict_routing = {raw}\n")
                with self.assertRaisesRegex(
                    _config.ConfigError, "execute.strict_routing.*boolean"
                ):
                    _config.load_config(root)


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


class LimitValues(unittest.TestCase):
    """T39: a limit the loop cannot compare against never fires.

    An unlimited run is a documented choice (D8, by omitting the key). A limit
    that is present but unusable is not: it reads as a ceiling and behaves like
    no ceiling, which is the difference between a run that halts at 2am and one
    that is still hanging at 8am.
    """

    def test_rejects_a_non_integer_limit(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, '[limits]\nexecutor_timeout_seconds = "1800"\n')
            with self.assertRaises(_config.ConfigError) as ctx:
                _config.load_config(root)
            self.assertIn("limits.executor_timeout_seconds", str(ctx.exception))

    def test_rejects_zero_rather_than_reading_it_as_unlimited(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "[limits]\nmax_iterations = 0\n")
            with self.assertRaises(_config.ConfigError) as ctx:
                _config.load_config(root)
            self.assertIn("omit the key", str(ctx.exception))

    def test_rejects_a_negative_limit(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "[limits]\nmax_minutes = -30\n")
            with self.assertRaises(_config.ConfigError):
                _config.load_config(root)

    def test_every_limit_key_is_checked(self):
        for key in _config.LIMIT_KEYS:
            with tempfile.TemporaryDirectory() as root:
                _write(root, f"[limits]\n{key} = 0\n")
                with self.assertRaises(_config.ConfigError, msg=key) as ctx:
                    _config.load_config(root)
                self.assertIn(f"limits.{key}", str(ctx.exception))

    def test_a_positive_integer_is_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "[limits]\nexecutor_timeout_seconds = 1800\n")
            limits = _config.load_config(root)["limits"]
            self.assertEqual(limits["executor_timeout_seconds"], 1800)


def audited_key_names(config):
    """Every key name the config declares, excluding the stage names themselves.

    A stage name is a namespace the user chooses (`[stages.whatever]` is legal),
    not a key with a documented default. Everything else in `defaults()` is a
    promise that something acts on it.
    """
    names = set()

    def walk(node, skip_own_keys=False):
        for key, value in node.items():
            if not skip_own_keys:
                names.add(key)
            if isinstance(value, dict):
                walk(value, skip_own_keys=(key == "stages"))

    walk(config)
    return names


def reader_sources():
    """`{relative path: text}` for every non-test script that may read a key.

    `_config.py` is excluded on purpose. Declaring a key and merging the user's
    value into the returned dict is exactly what `continue.in_turn` did for the
    whole of its life, so counting that as a read would make this check unable
    to fail for the reason it exists.
    """
    sources = {}
    for name in sorted(os.listdir(SCRIPTS)):
        if name.startswith("test_") or name == "_config.py":
            continue
        if not name.endswith((".py", ".sh")):
            continue
        with open(os.path.join(SCRIPTS, name), encoding="utf-8") as handle:
            sources[name] = handle.read()
    return sources


def unread_keys(names, sources):
    return sorted(
        name
        for name in names
        if not any(
            re.search(rf"\b{re.escape(name)}\b", text) for text in sources.values()
        )
    )


class EveryDeclaredKeyHasAReader(unittest.TestCase):
    """T39: a config key nothing reads is a promise the loop does not keep.

    This has bitten three times - `verify.max_rounds`, then
    `limits.executor_timeout_seconds`, `continue.in_turn`, and `continue.mode` -
    and each time it was found by somebody auditing by hand. The next one fails
    the Quick gate instead.

    The check is textual: a key named only in a comment counts as read. That is
    deliberate - `loop.sh` enforces the executor timeout while naming the key
    only in prose - and it is the limit of what a static scan can claim. What it
    catches is the case every one of those four was: a key nobody wired to
    anything at all.
    """

    def test_every_key_the_config_defaults_is_read_by_a_script(self):
        unread = unread_keys(audited_key_names(_config.defaults()), reader_sources())
        self.assertEqual(
            unread,
            [],
            "these keys are declared in _config.defaults() and read by no "
            f"non-test script: {', '.join(unread)}. Give each one a reader or "
            "remove it from the config, the schema, the example, and SKILL.md.",
        )

    def test_the_check_names_a_key_that_nothing_reads(self):
        # Without this the check could pass because the scan found nothing.
        config = _config.defaults()
        config["limits"]["nobody_reads_this_knob"] = None
        unread = unread_keys(audited_key_names(config), reader_sources())
        self.assertEqual(unread, ["nobody_reads_this_knob"])

    def test_the_scan_reaches_the_scripts_that_do_the_reading(self):
        sources = reader_sources()
        for name in ("detect_phase.py", "resolve_stage.py", "init_loop.py", "loop.sh"):
            self.assertIn(name, sources)
        self.assertNotIn("_config.py", sources)


if __name__ == "__main__":
    unittest.main()
