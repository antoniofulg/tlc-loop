#!/usr/bin/env python3
"""Run one command under a time bound and kill its whole tree when it expires.

`loop.sh` needs a bounded respawn (LOOP-06): a provider CLI that hangs produces
no output at all, and an unattended run has nobody to notice. `timeout(1)` is
not portable - absent on macOS without coreutils - and the two bash watchdogs
that stood here before both shipped a different job-control bug. This is the
standard library doing the same job without the job control.

Three properties are the whole reason this file exists.

**The command gets its own session, not a background job.** `start_new_session`
means one `killpg` reaches the command and everything it spawned. Bash's `set
-m` also makes a process group, but it makes a *background* one: a CLI that
reads the terminal is then stopped by `SIGTTIN`, `SIGTERM` to a stopped process
only queues, and the driver waits forever on a child that will never exit. A
new session has no controlling terminal, so that signal is never raised. The
trade is that the command cannot open `/dev/tty`; an executor that needs a
human at the keyboard was never compatible with an unattended run.

**The escalation is not behind the wait it exists to rescue.** `SIGKILL` is
sent after a bounded grace period, whatever the direct child did with `SIGTERM`
and whether or not it has been reaped. Sequencing it after an unbounded wait is
how the previous version turned a hung executor into a hung driver.

**Expiry is an exit code, not a file.** 124 is what `timeout(1)` reports for
the same event, so a transcript reads the same way whichever ran, and there is
no marker file to leak.

Usage:
    _spawn.py --timeout SECONDS <shell command line>

Exit codes:
    124        the command outlived --timeout and its process group was killed
    128 + N    the command died on signal N
    otherwise  the command's own exit code
"""

import argparse
import os
import signal
import subprocess
import sys

#: What an expiry reports, matching `timeout(1)`.
TIMED_OUT = 124

#: How long the group has to honour `SIGTERM` before `SIGKILL` lands. TERM is a
#: request, so a CLI that wants to flush its output can, and one that ignores
#: it costs this much and no more.
GRACE_SECONDS = 3


def _signal_group(pid, sig):
    """Signal the command's whole group. `start_new_session` makes pid the pgid.

    An already-empty group is the success case, not an error.
    """
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


def exit_status(returncode):
    """A shell's convention: a command killed by signal N reports 128 + N."""
    return 128 - returncode if returncode < 0 else returncode


def terminate(proc, grace=GRACE_SECONDS):
    """End the command's group. Bounded by `grace`, never by the child's cooperation."""
    _signal_group(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    # Unconditional. The direct child exiting says nothing about a grandchild it
    # spawned, which would otherwise keep running and keep the caller's stdout
    # open, and KILL is the one signal nothing can ignore.
    _signal_group(proc.pid, signal.SIGKILL)
    proc.wait()


def run(command, timeout, grace=GRACE_SECONDS):
    """Run `command` through a shell, bounded by `timeout` seconds.

    Returns the command's own exit status, or `TIMED_OUT` if the bound expired.
    """
    proc = subprocess.Popen(command, shell=True, start_new_session=True)
    try:
        return exit_status(proc.wait(timeout=timeout))
    except subprocess.TimeoutExpired:
        terminate(proc, grace)
        return TIMED_OUT


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="_spawn.py",
        description="Run a shell command line under a time bound.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        required=True,
        metavar="SECONDS",
        help="kill the command and its process group after this many seconds",
    )
    parser.add_argument("command", help="the shell command line to run")
    args = parser.parse_args(argv)
    return run(args.command, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
