"""Integration tests for `scripts/loop.sh` (T19).

Derived from the task's "Done when" criteria and LOOP-06: the driver breaks on
`phase=E` and on `phase=H` printing the line it broke on, spawns the resolved
respawn command on any other phase, and breaks rather than spinning on a line
it cannot parse.

T39 added the executor timeout: a respawn that outlives
`limits.executor_timeout_seconds` is killed and the expiry recorded as an
executor halt, so a hung provider CLI stops the run instead of holding it open
until morning. T41 moved the clock itself into `scripts/_spawn.py`; what these
tests own is the driver's half of it - that a bound is delegated, that an
expiry becomes a halt, and that nothing outlives a respawn either way.

`detect_phase`, `resolve_stage` and `update_loop` are stubbed. The driver never
runs a real provider CLI here and makes no network call: the "provider" is a
`/bin/sh -c` one-liner that touches a marker file.
"""

import glob
import os
import pty
import select
import signal
import subprocess
import tempfile
import time
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

#: Records the argv it was handed, so a test can assert what the driver asked
#: the single writer to record rather than only that it called something.
UPDATE_STUB = '''#!/usr/bin/env python3
import os, sys

with open(os.environ["STUB_UPDATE_ARGV"], "a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\\n")
code = int(os.environ.get("STUB_UPDATE_CODE", "0"))
if code:
    sys.stderr.write("stub update refused\\n")
sys.exit(code)
'''


class LoopShTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        self.detect_counter = os.path.join(self.root, "detect.count")
        self.resolve_counter = os.path.join(self.root, "resolve.count")
        self.marker = os.path.join(self.root, "spawned.txt")
        self.update_argv = os.path.join(self.root, "update.argv")
        self.detect_stub = self._write_stub("stub_detect.py", DETECT_STUB)
        self.resolve_stub = self._write_stub("stub_resolve.py", RESOLVE_STUB)
        self.update_stub = self._write_stub("stub_update.py", UPDATE_STUB)

    def _write_stub(self, name, body):
        path = os.path.join(self.root, name)
        with open(path, "w") as fh:
            fh.write(body)
        os.chmod(path, 0o755)
        return path

    def stub_env(self, steps, resolve_out=None, resolve_code=0, update_code=0):
        """The environment that points loop.sh at the stubs."""
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
                "LOOP_UPDATE_CMD": "python3 %s" % self.update_stub,
                "STUB_DETECT_COUNTER": self.detect_counter,
                "STUB_DETECT_STEPS": "||".join(steps),
                "STUB_RESOLVE_COUNTER": self.resolve_counter,
                "STUB_RESOLVE_OUT": resolve_out,
                "STUB_RESOLVE_CODE": str(resolve_code),
                "STUB_UPDATE_ARGV": self.update_argv,
                "STUB_UPDATE_CODE": str(update_code),
            }
        )
        return env

    def run_loop(self, steps, resolve_out=None, resolve_code=0, update_code=0):
        """Run loop.sh against the stubs and return the CompletedProcess."""
        return subprocess.run(
            ["bash", LOOP_SH, "demo", "--root", self.root],
            capture_output=True,
            text=True,
            env=self.stub_env(steps, resolve_out, resolve_code, update_code),
            timeout=60,
        )

    def recorded_updates(self):
        if not os.path.isfile(self.update_argv):
            return []
        with open(self.update_argv) as fh:
            return [line.strip() for line in fh if line.strip()]

    def survivors(self, pattern):
        """Processes still matching `pattern`, after a moment for the kill to land."""
        time.sleep(0.5)
        found = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
        return found.stdout.strip()

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


class TestExecutorTimeout(LoopShTestCase):
    """T39 / LOOP-06: a respawn that outlives its timeout is killed, not waited on.

    `limits.executor_timeout_seconds` arrives on the resolved line as
    `timeout=<seconds>`. A hung provider CLI is not an error and not a halt - it
    is silence - so something has to hold the clock. Since T41 that is
    `_spawn.py`; these tests assert the outcome the driver promises, whichever
    side of the boundary produces it.
    """

    #: Two levels deep on purpose. The shell the spawner starts is not the
    #: provider CLI, it is the CLI's parent; signalling the pid alone leaves the
    #: CLI orphaned and still holding the driver's stdout. Reading this run to
    #: EOF is therefore a direct test of whether the whole tree died.
    HANG = "kind=command provider=stub timeout=1 cmd=/bin/sh -c 'sleep 40'"

    def test_a_respawn_that_outlives_the_timeout_is_killed(self):
        started = time.monotonic()
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            resolve_out=self.HANG,
        )
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 20, "the driver waited for the hung respawn")
        self.assertEqual(run.returncode, 1, run.stderr)

    def test_the_whole_process_tree_dies_not_just_the_wrapper(self):
        # An orphaned provider CLI keeps its quota burning and keeps the pipe
        # open. `capture_output` reads to EOF, so a surviving grandchild shows
        # up as the driver appearing to take the full 40 seconds.
        started = time.monotonic()
        self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            resolve_out=self.HANG,
        )

        self.assertLess(time.monotonic() - started, 20)
        self.assertEqual(self.survivors("sleep 40"), "", "an orphan outlived the kill")

    def test_a_respawn_that_ignores_term_is_killed_anyway(self):
        # A CLI with its own TERM handler is not hypothetical, and TERM is a
        # request. Worse, `sh` passes an ignored signal through exec, so the
        # inner sleep inherits it. Only KILL ends this one.
        started = time.monotonic()
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            resolve_out=(
                "kind=command provider=stub timeout=1 cmd=/bin/sh -c "
                "'trap \"\" TERM; sleep 41'"
            ),
        )

        self.assertLess(time.monotonic() - started, 20, "TERM was the only attempt")
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(self.survivors("sleep 41"), "")

    def test_the_expiry_is_recorded_as_an_executor_halt(self):
        self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            resolve_out=self.HANG,
        )

        recorded = self.recorded_updates()
        self.assertEqual(len(recorded), 1, recorded)
        self.assertIn("--halt executor", recorded[0])
        self.assertIn("demo --root", recorded[0])
        self.assertIn("executor_timeout_seconds", recorded[0])

    def test_the_run_stops_on_the_halt_line_detection_then_reports(self):
        # The driver invents no second stop contract: it records the halt and
        # lets the next detect print it, so the last stdout line is a phase line.
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            resolve_out=self.HANG,
        )

        self.assertEqual(
            run.stdout.strip().splitlines()[-1],
            'phase=H action=halt reason=executor detail="killed"',
        )
        self.assertEqual(self.detect_calls(), 2)

    def test_a_respawn_inside_the_timeout_runs_untouched(self):
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                "phase=E action=done",
            ],
            resolve_out=(
                "kind=command provider=stub timeout=30 cmd=/bin/sh -c "
                "'printf x >> %s'" % self.marker
            ),
        )

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.spawns(), 1)
        self.assertEqual(self.recorded_updates(), [], "nothing to halt about")

    def test_a_failing_respawn_inside_the_timeout_still_breaks(self):
        # The watchdog must not swallow the command's own exit status.
        run = self.run_loop(
            ["phase=B action=execute_batch batch=P1 tasks=T1"],
            resolve_out="kind=command provider=stub timeout=30 cmd=/bin/sh -c 'exit 3'",
        )

        self.assertEqual(run.returncode, 2)
        self.assertIn("exited 3", run.stderr)
        self.assertEqual(self.recorded_updates(), [])

    def test_no_timeout_field_means_unlimited(self):
        # The default resolve_out carries no `timeout=`, and the respawn runs.
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                "phase=E action=done",
            ]
        )

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.spawns(), 1)

    def test_an_unbounded_respawn_runs_in_the_drivers_own_process_group(self):
        # "Unlimited" is not only "it still runs": with no bound there is no
        # spawner in the way, so the respawn stays in the foreground group it
        # would need to read a terminal. A bound is what moves it out.
        pgid_file = os.path.join(self.root, "pgid.txt")
        record = (
            "kind=command provider=stub cmd=/bin/sh -c "
            "'ps -o pgid= -p $$ > %s'" % pgid_file
        )

        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                "phase=E action=done",
            ],
            resolve_out=record,
        )
        with open(pgid_file) as handle:
            unbounded = handle.read().strip()

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(int(unbounded), os.getpgid(0))

    def test_a_bounded_respawn_runs_in_a_group_of_its_own(self):
        pgid_file = os.path.join(self.root, "pgid.txt")
        record = (
            "kind=command provider=stub timeout=30 cmd=/bin/sh -c "
            "'ps -o pgid= -p $$ > %s'" % pgid_file
        )

        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                "phase=E action=done",
            ],
            resolve_out=record,
        )
        with open(pgid_file) as handle:
            bounded = handle.read().strip()

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotEqual(
            int(bounded),
            os.getpgid(0),
            "a bounded respawn shares the driver's group, so a kill cannot "
            "single it out",
        )

    def test_a_respawn_inside_its_bound_leaves_nothing_behind(self):
        # The bound is 300s and the respawn takes milliseconds. Anything the
        # driver started to enforce that bound must be gone when the run ends:
        # a leftover holds the driver's stdout open for the full 300 seconds,
        # so `capture_output` - which reads to EOF - is the detector.
        started = time.monotonic()
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                "phase=E action=done",
            ],
            resolve_out=(
                "kind=command provider=stub timeout=300 cmd=/bin/sh -c "
                "'printf x >> %s'" % self.marker
            ),
        )
        elapsed = time.monotonic() - started

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.spawns(), 1)
        self.assertLess(elapsed, 20, "something outlived the respawn")
        self.assertEqual(self.survivors("sleep 300"), "")

    def test_an_expiry_leaves_no_temp_file_behind(self):
        pattern = os.path.join(
            os.environ.get("TMPDIR", "/tmp"), "tlc-loop-timeout-*"
        )
        before = set(glob.glob(pattern))

        self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            resolve_out=self.HANG,
        )

        self.assertEqual(set(glob.glob(pattern)) - before, set())

    def test_a_halt_that_cannot_be_recorded_breaks_rather_than_spinning(self):
        run = self.run_loop(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            resolve_out=self.HANG,
            update_code=1,
        )

        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.detect_calls(), 1, "an unrecordable halt must not loop")


class TestRespawnThatReadsTheTerminal(LoopShTestCase):
    """The blocker round 5 reproduced, driven through the real driver.

    Both preconditions are the project's own instructions: run `loop.sh` from a
    terminal, with `executor_timeout_seconds` set. A respawn that then reads
    that terminal used to stop on `SIGTTIN`, which the driver's `wait` never
    returned from - a 20 second bound ran two minutes and was still going, with
    no halt recorded. A pty is the only place that shows up.
    """

    #: Reads the terminal, then would hold it for ten minutes. `sleep 601` is
    #: what `pgrep` looks for afterwards.
    READS_TTY = (
        "kind=command provider=stub timeout=2 cmd=/bin/sh -c "
        "'printf READY; head -c 1 >/dev/null; sleep 601'"
    )

    def run_loop_under_a_pty(self, steps, resolve_out, deadline=45):
        """Run loop.sh as a session leader with a controlling terminal."""
        env = self.stub_env(steps, resolve_out)
        pid, fd = pty.fork()
        if pid == 0:  # pragma: no cover - replaced by execve
            try:
                os.execve(
                    "/bin/bash", ["bash", LOOP_SH, "demo", "--root", self.root], env
                )
            finally:
                os._exit(127)
        chunks = []
        status = None
        end = time.monotonic() + deadline
        while time.monotonic() < end:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                try:
                    data = os.read(fd, 4096)
                except OSError:
                    data = b""
                if data:
                    chunks.append(data)
                    continue
            reaped, wait_status = os.waitpid(pid, os.WNOHANG)
            if reaped:
                status = wait_status
                break
        os.close(fd)
        if status is None:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        return b"".join(chunks).decode(errors="replace"), status

    def test_the_driver_stops_instead_of_hanging_on_a_terminal_read(self):
        self.addCleanup(subprocess.run, ["pkill", "-f", "sleep 601"],
                        capture_output=True)
        started = time.monotonic()

        output, status = self.run_loop_under_a_pty(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            self.READS_TTY,
        )
        elapsed = time.monotonic() - started

        self.assertIsNotNone(
            status, "the driver never exited: the terminal read hung it"
        )
        self.assertIn("READY", output, "the respawn never reached the terminal")
        self.assertLess(elapsed, 40, "the bound was not enforced under a pty")
        self.assertEqual(os.waitstatus_to_exitcode(status), 1, output)
        self.assertIn("phase=H action=halt reason=executor", output)
        self.assertEqual(self.survivors("sleep 601"), "")

    def test_the_expiry_under_a_pty_is_still_recorded_as_an_executor_halt(self):
        self.addCleanup(subprocess.run, ["pkill", "-f", "sleep 601"],
                        capture_output=True)

        self.run_loop_under_a_pty(
            [
                "phase=B action=execute_batch batch=P1 tasks=T1",
                'phase=H action=halt reason=executor detail="killed"',
            ],
            self.READS_TTY,
        )

        recorded = self.recorded_updates()
        self.assertEqual(len(recorded), 1, recorded)
        self.assertIn("--halt executor", recorded[0])


class TestTemporaryFiles(LoopShTestCase):
    """T43: the driver's own temp file outlives no exit path, signals included.

    `LOOP_EVIDENCE` is where codex writes its result, so the driver mktemps one
    when the caller names none. A run left overnight is exactly the run somebody
    terminates from another window, and a driver that leaks a file per run leaks
    one per night.
    """

    PATTERN = os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "tlc-loop-evidence-*"
    )

    def test_the_evidence_file_is_removed_when_the_driver_is_signalled(self):
        before = set(glob.glob(self.PATTERN))
        env = self.stub_env(
            ["phase=B action=execute_batch batch=P1 tasks=T1", "phase=E action=done"],
            resolve_out="kind=command provider=stub cmd=/bin/sh -c 'sleep 22'",
        )
        env["LOOP_EVIDENCE"] = ""
        driver = subprocess.Popen(
            ["bash", LOOP_SH, "demo", "--root", self.root],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
        self.addCleanup(subprocess.run, ["pkill", "-f", "sleep 22"],
                        capture_output=True)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not set(glob.glob(self.PATTERN)) - before:
            time.sleep(0.1)
        created = set(glob.glob(self.PATTERN)) - before
        for path in created:
            self.addCleanup(lambda p=path: os.path.isfile(p) and os.remove(p))

        self.assertTrue(created, "the driver never created an evidence file")
        os.killpg(driver.pid, signal.SIGTERM)
        driver.wait(timeout=20)
        time.sleep(0.5)

        self.assertEqual(
            set(glob.glob(self.PATTERN)) - before,
            set(),
            "a terminated driver left its evidence file behind",
        )


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
