"""Unit tests for validate_routing.py - the read-only pre-approval route gate."""

import os
import subprocess
import sys
import tempfile
import unittest


SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_routing.py")


def _write(root, relative, text):
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def _snapshot(root):
    out = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            with open(path, "rb") as handle:
                out[os.path.relpath(path, root)] = handle.read()
    return out


class ValidateRouting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.feature_dir = os.path.join(self.root, ".specs", "features", "demo")

    def write_tasks(self, text):
        return _write(self.root, ".specs/features/demo/tasks.md", text)

    def write_config(self, text):
        return _write(self.root, ".specs/loop.config.toml", text)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, SCRIPT, *args], capture_output=True, text=True
        )

    def test_valid_plan_prints_ordered_route_map(self):
        self.write_config("[stages.backend]\nprovider = 'auto'\n")
        self.write_tasks(
            "### Phase 1: Foundation\n\n"
            "### Phase 2: API\n**Stage:** backend\n"
        )
        proc = self.run_cli("demo", "--root", self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            proc.stdout.splitlines(),
            [
                "route:",
                "  Phase 1: Foundation -> implement",
                "  Phase 2: API -> backend",
            ],
        )

    def test_invalid_plan_reports_every_phase_error(self):
        self.write_tasks(
            "### Phase 1: Verification\n**Stage:** verify\n"
            "### Phase 2: Typo\n**Stage:** backned\n"
        )
        proc = self.run_cli("demo", "--root", self.root)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Phase 1", proc.stderr)
        self.assertIn("reserved", proc.stderr)
        self.assertIn("Phase 2", proc.stderr)
        self.assertIn("not configured", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_missing_tasks_file_exits_one_and_names_it(self):
        proc = self.run_cli("demo", "--root", self.root)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("tasks.md", proc.stderr)

    def test_bad_usage_exits_two(self):
        self.assertEqual(self.run_cli().returncode, 2)

    def test_validation_is_read_only(self):
        self.write_tasks("### Phase 1: Legacy\n")
        before = _snapshot(self.root)
        proc = self.run_cli("demo", "--root", self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(_snapshot(self.root), before)


if __name__ == "__main__":
    unittest.main()
