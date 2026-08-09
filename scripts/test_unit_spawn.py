"""Unit tests for `scripts/_spawn.py` (T41, LOOP-06).

Derived from the task's "Done when" criteria: a bounded command returns its own
status, one that outlives the bound is killed along with everything it spawned,
a child that ignores `SIGTERM` is killed anyway, a child that reads a terminal
does not stop and deadlock the caller, and an expiry is distinguishable from an
ordinary non-zero exit.

Every case ends the same way: `pgrep` for a token unique to that test must find
nothing. A timeout that returns while the process tree is still alive is the
failure this file exists to catch, and it is invisible to an exit-code
assertion alone.

Cleanup then repeats that check as an assertion (T46). It has to escalate to
`SIGKILL` to do it: one probe behaviour ignores `SIGTERM` deliberately, and it
is the behaviour left running whenever the spawner is the thing that broke, so
a polite `pkill` reaps only the processes that were never the problem.

The terminal case runs the spawner under a real pty (`pty.fork`, which makes the
child a session leader with the slave as its controlling terminal). That is the
environment a user runs `loop.sh` in and the only one in which the previous bash
watchdog deadlocked, so skipping it would leave the blocker untested.

No provider CLI runs here and nothing touches the network: the only subprocesses
are this interpreter running a local probe script, and `pgrep`.
"""

import os
import pty
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPTS = os.path.dirname(os.path.realpath(__file__))
SPAWN = os.path.join(SCRIPTS, "_spawn.py")

#: How long `reap` waits for each signal to land before escalating or giving up.
REAP_GRACE = 3.0

#: One probe, several behaviours, and its token sits in argv so `pgrep -f` can
#: find every process of the tree that outlived a kill.
PROBE = '''#!/usr/bin/env python3
import os, signal, subprocess, sys, time

token, behaviour = sys.argv[1], sys.argv[2]

if behaviour == "exit":
    sys.exit(int(sys.argv[3]))
if behaviour == "selfkill":
    os.kill(os.getpid(), signal.SIGKILL)
if behaviour == "ignore-term":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if behaviour == "grandchild":
    subprocess.Popen([sys.executable, __file__, token + "-child", "hang"])
if behaviour == "read":
    sys.stdout.write("READY\\n")
    sys.stdout.flush()
    sys.stdin.read(1)
time.sleep(600)
'''


def matching(pattern):
    """Pids whose argv contains `pattern`, as `pgrep -f` prints them."""
    found = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    return found.stdout.strip()


def reap(pattern, grace=REAP_GRACE):
    """Kill everything matching `pattern`, escalating past `SIGTERM`.

    Returns whatever is still alive at the end, so the caller can assert on it.

    `pkill` alone sends `SIGTERM`, and one probe behaviour ignores `SIGTERM` on
    purpose - which is exactly the behaviour left running when the spawner is
    broken. So the polite signal reaped only the processes that were never the
    problem: eleven `sleep 600` probes survived a sensor run and needed
    `pkill -9` by hand. `SIGKILL` cannot be ignored, so the escalation ends.
    """
    for escalation in ([], ["-9"]):
        subprocess.run(["pkill", *escalation, "-f", pattern], capture_output=True)
        deadline = time.monotonic() + grace / 2
        while time.monotonic() < deadline:
            if not matching(pattern):
                return ""
            time.sleep(0.1)
    return matching(pattern)


class SpawnTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.probe = os.path.join(self.tmp.name, "probe.py")
        with open(self.probe, "w") as handle:
            handle.write(PROBE)
        os.chmod(self.probe, 0o755)
        self._token = "tlcspawn%d" % os.getpid()

    def token(self, name):
        """A token unique to this test, carried in the probe's own argv."""
        unique = "%s-%s" % (self._token, name)
        # Even a failing test must not leave a `sleep 600` behind - which is
        # when it matters, because a spawner that works leaves nothing to reap.
        # So cleanup escalates to `SIGKILL` and then *asserts* the tree is gone
        # rather than assuming the signal was enough.
        self.addCleanup(self.assert_reaped, unique)
        return unique

    def assert_reaped(self, pattern):
        survivors = reap(pattern)
        self.assertEqual(
            survivors,
            "",
            "probe processes survived cleanup and are still running: %s" % survivors,
        )

    def command(self, token, *args):
        return " ".join([sys.executable, self.probe, token, *args])

    def spawn(self, timeout, command):
        """Run `_spawn.py` and return the CompletedProcess."""
        return subprocess.run(
            [sys.executable, SPAWN, "--timeout", str(timeout), "--", command],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def survivors(self, token):
        """Processes still matching `token`, after a moment for the kill to land."""
        time.sleep(0.5)
        return matching(token)


class TestUnderTheBound(SpawnTestCase):
    """A command that finishes in time is handed back untouched."""

    def test_a_command_that_completes_returns_its_own_exit_code(self):
        token = self.token("quick")

        run = self.spawn(30, self.command(token, "exit", "0"))

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.survivors(token), "")

    def test_a_failing_command_returns_its_own_status_not_the_expiry_code(self):
        token = self.token("fails")

        run = self.spawn(30, self.command(token, "exit", "7"))

        self.assertEqual(run.returncode, 7, run.stderr)
        self.assertEqual(self.survivors(token), "")

    def test_a_command_killed_by_a_signal_is_not_reported_as_an_expiry(self):
        # 128 + SIGKILL, the shell's own convention. An expiry says 124, so the
        # caller can tell "I killed it at the limit" from "it died on a signal".
        token = self.token("signalled")

        run = self.spawn(30, self.command(token, "selfkill"))

        self.assertEqual(run.returncode, 128 + signal.SIGKILL)
        self.assertEqual(self.survivors(token), "")


class TestOverTheBound(SpawnTestCase):
    """A command that outlives its bound is killed, and so is its whole tree."""

    def test_a_command_that_outlives_the_bound_reports_the_expiry_code(self):
        token = self.token("hangs")
        started = time.monotonic()

        run = self.spawn(1, self.command(token, "hang"))

        self.assertEqual(run.returncode, 124, run.stderr)
        self.assertLess(
            time.monotonic() - started, 30, "the spawner waited for the hung command"
        )
        self.assertEqual(self.survivors(token), "")

    def test_a_command_that_ignores_term_is_killed_anyway(self):
        token = self.token("stubborn")

        run = self.spawn(1, self.command(token, "ignore-term"))

        self.assertEqual(run.returncode, 124, run.stderr)
        self.assertEqual(
            self.survivors(token), "", "SIGTERM was the only attempt made"
        )

    def test_a_grandchild_the_command_spawned_dies_with_it(self):
        # A provider CLI is a wrapper around another process at least as often
        # as it is not. Killing the pid alone orphans that one, which then keeps
        # running and keeps the caller's stdout open.
        token = self.token("family")

        run = self.spawn(2, self.command(token, "grandchild"))

        self.assertEqual(run.returncode, 124, run.stderr)
        self.assertEqual(self.survivors(token), "", "a grandchild outlived the kill")


class TestTerminalReadingChild(SpawnTestCase):
    """The blocker round 5 reproduced: a child that reads the terminal.

    Under bash job control the child is a background job of the driver's
    terminal, so the kernel stops it with `SIGTTIN`; `SIGTERM` to a stopped
    process only queues, and the wait never returns. A pty is the only place
    this shows up, so the test allocates one.
    """

    def _drain(self, fd, pid, deadline):
        """Read the pty until the spawner exits. Returns (output, wait status)."""
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
        return b"".join(chunks).decode(errors="replace"), status

    def test_a_child_that_reads_the_terminal_does_not_deadlock_the_spawner(self):
        token = self.token("tty")
        command = self.command(token, "read")
        started = time.monotonic()

        pid, fd = pty.fork()
        if pid == 0:  # pragma: no cover - replaced by execv
            try:
                os.execv(
                    sys.executable,
                    [sys.executable, SPAWN, "--timeout", "2", "--", command],
                )
            finally:
                os._exit(127)
        output, status = self._drain(fd, pid, deadline=40)

        if status is None:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            self.fail("the spawner never exited: the terminal read deadlocked it")
        self.assertIn("READY", output, "the child never got to read the terminal")
        self.assertEqual(os.waitstatus_to_exitcode(status), 124)
        self.assertLess(
            time.monotonic() - started, 35, "the bound was not enforced under a pty"
        )
        self.assertEqual(self.survivors(token), "")


if __name__ == "__main__":
    unittest.main()
