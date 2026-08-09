"""Unit tests for _routing - phase Stage validation and effective routes."""

import unittest

import _config
import _routing


def _phase(number, stage, title=None):
    return {
        "number": number,
        "title": title or f"Phase {number}",
        "declared_stage": stage,
        "tasks": [f"T{number}"],
    }


def _config_with(*stages, strict=False):
    config = _config.defaults()
    config["execute"]["strict_routing"] = strict
    for stage in stages:
        config["stages"][stage] = {"provider": "auto", "model": None, "effort": None}
    return config


class EffectiveStage(unittest.TestCase):
    def test_explicit_configured_stage_is_preserved(self):
        routed = _routing.resolve([_phase(1, "backend")], _config_with("backend"))
        self.assertEqual(routed[0]["effective_stage"], "backend")
        self.assertEqual(routed[0]["declared_stage"], "backend")

    def test_missing_stage_falls_back_to_implement_when_not_strict(self):
        routed = _routing.resolve([_phase(1, None)], _config_with())
        self.assertEqual(routed[0]["effective_stage"], "implement")

    def test_custom_kebab_case_stage_is_supported(self):
        routed = _routing.resolve(
            [_phase(1, "backend-api")], _config_with("backend-api")
        )
        self.assertEqual(routed[0]["effective_stage"], "backend-api")


class InvalidRoutes(unittest.TestCase):
    def assert_error(self, phases, config, *fragments):
        with self.assertRaises(_routing.RoutingError) as ctx:
            _routing.resolve(phases, config)
        message = str(ctx.exception)
        for fragment in fragments:
            self.assertIn(fragment, message)
        return ctx.exception

    def test_missing_stage_is_rejected_in_strict_mode(self):
        self.assert_error(
            [_phase(1, None)], _config_with(strict=True), "Phase 1", "missing Stage"
        )

    def test_unknown_explicit_stage_never_falls_back(self):
        self.assert_error(
            [_phase(1, "backned")], _config_with(), "Phase 1", "backned", "not configured"
        )

    def test_reserved_runtime_stages_are_rejected(self):
        for stage in ("verify", "fix"):
            with self.subTest(stage=stage):
                self.assert_error(
                    [_phase(1, stage)], _config_with(), "Phase 1", stage, "reserved"
                )

    def test_malformed_stage_is_rejected(self):
        for stage in ("Backend", "backend_api", "", "-backend"):
            with self.subTest(stage=stage):
                self.assert_error(
                    [_phase(1, stage)], _config_with(stage), "Phase 1", "kebab-case"
                )

    def test_all_route_errors_are_reported_together(self):
        error = self.assert_error(
            [_phase(1, None), _phase(2, "verify"), _phase(3, "missing")],
            _config_with(strict=True),
            "Phase 1",
            "Phase 2",
            "Phase 3",
        )
        self.assertEqual(len(error.errors), 3)


if __name__ == "__main__":
    unittest.main()
