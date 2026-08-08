"""Unit tests for _state_io - the loop.json codec (T2, LOOP-01).

Derived from T2's "Done when" criteria and the loop.json shape in design.md.
LOOP-01 AC 5 makes this module the single writer, so the codec must fail loudly
on anything it did not write itself, and must never leave a half-written file.
"""

import json
import os
import tempfile
import unittest

import _state_io


def _feature_dir(root, feature="demo"):
    path = os.path.join(root, ".specs", "features", feature)
    os.makedirs(path, exist_ok=True)
    return path


def _write_raw(root, text, feature="demo"):
    path = os.path.join(_feature_dir(root, feature), "loop.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class NewState(unittest.TestCase):
    def test_returns_the_documented_initial_shape(self):
        state = _state_io.new_state("demo", "ship demo end to end", "claude")
        self.assertEqual(state["feature"], "demo")
        self.assertEqual(state["objective"], "ship demo end to end")
        self.assertEqual(state["harness_resolved"], "claude")
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["iteration"], 0)
        self.assertEqual(state["current_batch"], [])
        self.assertIsNone(state["current_task"])
        self.assertEqual(state["no_diff_tasks"], [])
        self.assertEqual(state["reconciled"], [])
        self.assertEqual(
            state["verify"],
            {"rounds": 0, "last_verdict": None, "last_report": None, "gaps_open": 0,
             "verified_at": None},
        )
        self.assertEqual(state["counters"]["iterations_without_commit"], 0)
        self.assertEqual(state["counters"]["gate_attempts"], {})
        self.assertIsInstance(state["counters"]["started_at_ms"], int)
        self.assertEqual(state["halt"], {"reason": None, "detail": None})
        self.assertEqual(state["iterations"], [])

    def test_completed_tasks_is_absent_by_design(self):
        # design.md: completion is derived from git trailers every run (D3).
        state = _state_io.new_state("demo", "obj", "claude")
        self.assertNotIn("completed_tasks", state)


class RoundTrip(unittest.TestCase):
    def test_save_then_load_returns_an_equal_state(self):
        with tempfile.TemporaryDirectory() as root:
            _feature_dir(root)
            state = _state_io.new_state("demo", "ship it", "codex")
            state["iteration"] = 4
            state["no_diff_tasks"] = ["T4"]
            _state_io.save("demo", root, state)
            self.assertEqual(_state_io.load("demo", root), state)

    def test_a_recorded_reconciliation_survives_the_round_trip(self):
        # T31 / LOOP-01 AC 5: the record is durable, not a print.
        with tempfile.TemporaryDirectory() as root:
            _feature_dir(root)
            state = _state_io.new_state("demo", "ship it", "codex")
            state["reconciled"] = [{"task": "T4", "winner": "git", "at": "2026-08-08T00:00:00Z"}]
            _state_io.save("demo", root, state)
            self.assertEqual(
                _state_io.load("demo", root)["reconciled"],
                [{"task": "T4", "winner": "git", "at": "2026-08-08T00:00:00Z"}],
            )

    def test_a_non_list_reconciled_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            _feature_dir(root)
            state = _state_io.new_state("demo", "ship it", "codex")
            state["reconciled"] = {"T4": "git"}
            with self.assertRaises(_state_io.StateError) as ctx:
                _state_io.save("demo", root, state)
            self.assertIn("reconciled must be a list", str(ctx.exception))

    def test_save_writes_indent_2_and_sorted_keys(self):
        with tempfile.TemporaryDirectory() as root:
            _feature_dir(root)
            state = _state_io.new_state("demo", "ship it", "codex")
            _state_io.save("demo", root, state)
            with open(_state_io.state_path("demo", root), encoding="utf-8") as fh:
                text = fh.read()
            self.assertEqual(text, json.dumps(state, indent=2, sort_keys=True) + "\n")
            # indent=2: every top-level key sits at exactly two spaces.
            top_level = [
                ln for ln in text.splitlines() if ln.startswith('  "') and not ln.startswith("   ")
            ]
            self.assertIn('  "created_at": ', "\n".join(top_level) + " ")
            # sort_keys=True: top-level keys appear in sorted order.
            emitted = [ln.split('"')[1] for ln in top_level]
            self.assertEqual(emitted, sorted(state.keys()))


class MalformedJson(unittest.TestCase):
    def test_load_raises_stateerror_naming_the_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = _write_raw(root, "{ not json")
            with self.assertRaises(_state_io.StateError) as ctx:
                _state_io.load("demo", root)
            self.assertIn(path, str(ctx.exception))

    def test_load_raises_when_the_document_is_not_an_object(self):
        with tempfile.TemporaryDirectory() as root:
            _write_raw(root, "[1, 2, 3]")
            with self.assertRaises(_state_io.StateError):
                _state_io.load("demo", root)


class SchemaValidation(unittest.TestCase):
    def test_load_rejects_an_unknown_status_value(self):
        with tempfile.TemporaryDirectory() as root:
            state = _state_io.new_state("demo", "obj", "claude")
            state["status"] = "sleepy"
            _write_raw(root, json.dumps(state))
            with self.assertRaises(_state_io.StateError) as ctx:
                _state_io.load("demo", root)
            self.assertIn("status", str(ctx.exception))
            self.assertIn("sleepy", str(ctx.exception))

    def test_load_accepts_every_documented_status_value(self):
        with tempfile.TemporaryDirectory() as root:
            for status in ("active", "blocked", "halted", "complete"):
                state = _state_io.new_state("demo", "obj", "claude")
                state["status"] = status
                _write_raw(root, json.dumps(state))
                self.assertEqual(_state_io.load("demo", root)["status"], status)

    def test_load_rejects_a_missing_required_key(self):
        with tempfile.TemporaryDirectory() as root:
            state = _state_io.new_state("demo", "obj", "claude")
            del state["objective"]
            _write_raw(root, json.dumps(state))
            with self.assertRaises(_state_io.StateError) as ctx:
                _state_io.load("demo", root)
            self.assertIn("objective", str(ctx.exception))

    def test_save_rejects_an_unknown_status_value(self):
        with tempfile.TemporaryDirectory() as root:
            _feature_dir(root)
            state = _state_io.new_state("demo", "obj", "claude")
            state["status"] = "sleepy"
            with self.assertRaises(_state_io.StateError):
                _state_io.save("demo", root, state)

    def test_save_rejects_a_missing_required_key(self):
        with tempfile.TemporaryDirectory() as root:
            _feature_dir(root)
            state = _state_io.new_state("demo", "obj", "claude")
            del state["counters"]
            with self.assertRaises(_state_io.StateError) as ctx:
                _state_io.save("demo", root, state)
            self.assertIn("counters", str(ctx.exception))


class Atomicity(unittest.TestCase):
    def test_a_failed_write_leaves_no_partial_file_and_no_temp_leftovers(self):
        with tempfile.TemporaryDirectory() as root:
            fdir = _feature_dir(root)
            good = _state_io.new_state("demo", "obj", "claude")
            _state_io.save("demo", root, good)
            with open(_state_io.state_path("demo", root), "rb") as fh:
                before_bytes = fh.read()
            before_entries = sorted(os.listdir(fdir))

            broken = _state_io.new_state("demo", "obj", "claude")
            broken["iterations"] = [{"n": object()}]  # not JSON-serialisable
            with self.assertRaises(TypeError):
                _state_io.save("demo", root, broken)

            with open(_state_io.state_path("demo", root), "rb") as fh:
                self.assertEqual(fh.read(), before_bytes)
            self.assertEqual(sorted(os.listdir(fdir)), before_entries)

    def test_a_successful_write_replaces_the_file_and_leaves_no_temp(self):
        with tempfile.TemporaryDirectory() as root:
            fdir = _feature_dir(root)
            state = _state_io.new_state("demo", "obj", "claude")
            _state_io.save("demo", root, state)
            state["iteration"] = 9
            _state_io.save("demo", root, state)
            self.assertEqual(os.listdir(fdir), ["loop.json"])
            self.assertEqual(_state_io.load("demo", root)["iteration"], 9)


if __name__ == "__main__":
    unittest.main()
