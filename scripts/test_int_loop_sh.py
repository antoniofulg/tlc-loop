"""Integration tests for `scripts/loop.sh` (T19).

Derived from the task's "Done when" criteria and LOOP-06: the driver breaks on
`phase=E` and on `phase=H` printing the line it broke on, spawns the resolved
respawn command on any other phase, and breaks rather than spinning on a line
it cannot parse.

`detect_phase` and `resolve_stage` are stubbed. The driver never runs a real
provider CLI here and makes no network call: the "provider" is a `/bin/sh -c`
one-liner that touches a marker file.
"""

import os
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.realpath(__file__))
LOOP_SH = os.path.join(SCRIPTS, "loop.sh")

#: Prints one scripted step per invocation, advancing a counter file. The last
#: step repeats forever, so a driver that spins is caught by the counter rather
#: than by a hanging test.
DETECT_STUB = '''#!/usr/bin/env python3
import os, sys

counter = os.environ["STUB_DETECT_COUNTER"]
steps = os.environ["STUB_DETECT_STEPS"].split("||")
try:
    with open(counter) as fh:
        n = int(fh.read().strip())
except (OSError, ValueError):
    n = 0
with open(counter, "w") as fh:
    fh.write(str(n + 1))
step = steps[min(n, len(steps) - 1)]
if step.startswith("EXIT:"):
    sys.stderr.write("stub detect refused\\n")
    sys.exit(int(step[len("EXIT:"):]))
sys.stdout.write(step + "\\n")
'''

RESOLVE_STUB = '''#!/usr/bin/env python3
import os, sys

code = int(os.environ.get("STUB_RESOLVE_CODE", "0"))
with open(os.environ["STUB_RESOLVE_COUNTER"], "a") as fh:
    fh.write("call\\n")
if code:
    sys.stderr.write("stub resolve refused\\n")
    sys.exit(code)
sys.stdout.write(os.environ["STUB_RESOLVE_OUT"] + "\\n")
'''


class LoopShTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        self.detect_counter = os.path.join(self.root, "detect.count")
        self.resolve_counter = os.path.join(self.root, "resolve.count")
        self.marker = os.path.join(self.root, "spawned.txt")
        self.detect_stub = self._write_stub("stub_detect.py", DETECT_STUB)
        self.resolve_stub = self._write_stub("stub_resolve.py", RESOLVE_STUB)

    def _write_stub(self, name, body):
        path = os.path.join(self.root, name)
        with open(path, "w") as fh:
            fh.write(body)
        os.chmod(path, 0o755)
        return path

    def run_loop(self, steps, resolve_out=None, resolve_code=0):
        """Run loop.sh against the stubs and return the CompletedProcess."""
        if resolve_out is None:
            resolve_out = (
                "kind=command provider=stub cmd=/bin/sh -c "
                "'printf x >> %s'" % self.marker
            )
        env = dict(os.environ)
        env.update(
            {
                "LOOP_DETECT_CMD": "python3 %s" % self.detect_stub,
                "LOOP_RESOLVE_CMD": "python3 %s" % self.resolve_stub,
                "STUB_DETECT_COUNTER": self.detect_counter,
                "STUB_DETECT_STEPS": "||".join(steps),
                "STUB_RESOLVE_COUNTER": self.resolve_counter,
                "STUB_RESOLVE_OUT": resolve_out,
                "STUB_RESOLVE_CODE": str(resolve_code),
            }
        )
        return subprocess.run(
            ["bash", LOOP_SH, "demo", "--root", self.root],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    def detect_calls(self):
        with open(self.detect_counter) as fh:
            return int(fh.read().strip())

    def resolve_calls(self):
        if not os.path.isfile(self.resolve_counter):
            return 0
        with open(self.resolve_counter) as fh:
            return len([line for line in fh if line.strip()])

    def spawns(self):
        if not os.path.isfile(self.marker):
            return 0
        with open(self.marker) as fh:
            return len(fh.read())


class TestTerminalPhases(LoopShTestCase):
    """The loop breaks on phase=E and on phase=H, printing the line."""

    def test_breaks_on_phase_e_printing_the_line(self):
        done = self.run_loop(["phase=E action=done"])

        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("phase=E action=done", done.stdout)
        self.assertEqual(self.detect_calls(), 1)
        self.assertEqual(self.spawns(), 0, "a terminal phase must not respawn")

    def test_breaks_on_phase_h_printing_the_line(self):
        line = 'phase=H action=halt reason=gate_stuck detail="T4 gate failed 4 times, limit 3"'

        halted = self.run_loop([line])

        self.assertNotEqual(halted.returncode, 0, "a halt is not a success exit")
        self.assertIn(line, halted.stdout)
        self.assertEqual(self.detect_calls(), 1)
        self.assertEqual(self.spawns(), 0, "a halt must not respawn")

    def test_halt_and_done_do_not_share_an_exit_code(self):
        halted = self.run_loop(['phase=H action=halt reason=limit detail="x"'])
        self.setUp()
        done = self.run_loop(["phase=E action=done"])

        self.assertNotEqual(halted.returncode, done.returncode)


class TestSpawn(LoopShTestCase):
    """Any non-terminal phase spawns the resolved respawn command."""

    def test_spawns_once_then_terminates(self):
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1,T2",
                "phase=E action=done",
            ]
        )

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.spawns(), 1, "exactly one respawn between the two detects")
        self.assertEqual(self.resolve_calls(), 1)
        self.assertEqual(self.detect_calls(), 2)
        self.assertIn("phase=B action=execute_batch batch=P1 tasks=T1,T2", run.stdout)
        self.assertIn("phase=E action=done", run.stdout)

    def test_spawns_for_every_non_terminal_phase(self):
        run = self.run_loop(
            [
                "phase=0 action=bootstrap",
                "phase=B action=execute_batch batch=P1 tasks=T1",
                "phase=V action=verify round=1",
                "phase=F action=fix round=1",
                "phase=E action=done",
            ]
        )

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.spawns(), 4)
        self.assertEqual(self.detect_calls(), 5)

    def test_asks_the_resolver_for_the_continue_respawn_stage(self):
        stub = os.path.join(self.root, "argv_resolve.py")
        with open(stub, "w") as fh:
            fh.write(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "open(os.environ['STUB_ARGV'], 'w').write(' '.join(sys.argv[1:]))\n"
                "sys.stdout.write('kind=command provider=stub cmd=/bin/true\\n')\n"
            )
        argv_file = os.path.join(self.root, "argv.txt")
        env = dict(os.environ)
        env.update(
            {
                "LOOP_DETECT_CMD": "python3 %s" % self.detect_stub,
                "LOOP_RESOLVE_CMD": "python3 %s" % stub,
                "STUB_DETECT_COUNTER": self.detect_counter,
                "STUB_DETECT_STEPS": "phase=B action=execute_batch batch=P1 tasks=T1"
                "||phase=E action=done",
                "STUB_ARGV": argv_file,
            }
        )
        subprocess.run(
            ["bash", LOOP_SH, "demo", "--root", self.root],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

        with open(argv_file) as fh:
            argv = fh.read()
        self.assertIn("--stage continue.respawn", argv)
        self.assertIn("--feature demo", argv)

    def test_a_respawn_with_no_command_breaks(self):
        run = self.run_loop(
            ["phase=B action=execute_batch batch=P1 tasks=T1"],
            resolve_out="kind=agent provider=claude model=opus effort=high",
        )

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1)
        self.assertIn("kind=agent", run.stderr)


class TestBreaksRatherThanSpinning(LoopShTestCase):
    """Nothing the driver cannot act on may become a tight loop."""

    def test_unparseable_line_breaks_after_one_detect(self):
        run = self.run_loop(["detect_phase blew up sideways"])

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1, "an unparseable line must not be retried")
        self.assertEqual(self.spawns(), 0)
        self.assertIn("detect_phase blew up sideways", run.stderr)

    def test_unknown_phase_letter_breaks(self):
        run = self.run_loop(["phase=Z action=improvise"])

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1)
        self.assertEqual(self.spawns(), 0)

    def test_empty_detect_output_breaks(self):
        run = self.run_loop([""])

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1)
        self.assertEqual(self.spawns(), 0)

    def test_detect_exiting_non_zero_breaks(self):
        run = self.run_loop(["EXIT:1"])

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1)
        self.assertEqual(self.spawns(), 0)

    def test_a_failing_respawn_breaks(self):
        run = self.run_loop(
            ["phase=B action=execute_batch batch=P1 tasks=T1"],
            resolve_out="kind=command provider=stub cmd=/bin/sh -c 'exit 3'",
        )

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1, "a failing respawn must not be retried")
        self.assertIn("exited 3", run.stderr)

    def test_a_failing_resolver_breaks(self):
        run = self.run_loop(
            ["phase=B action=execute_batch batch=P1 tasks=T1"],
            resolve_code=2,
        )

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1)
        self.assertEqual(self.spawns(), 0)


class TestSyntax(unittest.TestCase):
    def test_bash_n_passes(self):
        checked = subprocess.run(
            ["bash", "-n", LOOP_SH], capture_output=True, text=True
        )

        self.assertEqual(checked.returncode, 0, checked.stderr)


class TestInvocation(LoopShTestCase):
    def test_a_missing_feature_is_refused(self):
        run = subprocess.run(
            ["bash", LOOP_SH], capture_output=True, text=True, timeout=60
        )

        self.assertEqual(run.returncode, 2)
        self.assertIn("usage", run.stderr.lower())


if __name__ == "__main__":
    unittest.main()
