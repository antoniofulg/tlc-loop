"""Unit tests for finish_loop.py - the only path to the done-signature.

The incident this file exists for: a verifier passed commit `V`, two further
commits landed, the detector correctly answered
`phase=H reason=verify_exhausted`, and the signature was printed anyway. It was
printed by a model following a prose instruction, so nothing deterministic stood
between a stale tree and a success claim.

`finish_loop.py` is that thing. It re-derives the situation itself, records
completion through the single writer, re-checks that nothing moved underneath
it, and only then prints the signature as its last line. Every refusal below is
a line the old prose branch would have printed.

`--preflight <base>` is the same battery of checks with one more - the base ref
must be an ancestor of HEAD - and no mutation and no signature. It answers
"is this safe to publish", which is a different question from "is this done".

The fixture is `DetectPhaseCase`: this skill plus a stub sibling, over a real
tmpdir repository. The sibling's `check_commit.py` joins it because the happy
path runs through a real seal commit - an unsealed report leaves the tree dirty,
which is itself a refusal.
"""

import os
import subprocess
import sys
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

from test_unit_checkpoint import CHECK_COMMIT_STUB  # noqa: E402
from test_unit_detect_phase import DetectPhaseCase, _git  # noqa: E402

SIGNATURE = "__TLC_LOOP__ feature=demo verify=PASS"

PASS_REPORT = "## Validation: demo - PASS\n\nEvidence: scripts/a.py:12\n"

#: Stands in for `update_loop.py` and lands a commit before delegating to the
#: real one. It is how the tests reach the one window `finish_loop.py` cannot
#: close by checking first: the tree moving *while* completion is recorded.
SNEAKY_UPDATE_STUB = '''#!/usr/bin/env python3
import os, subprocess, sys

here = os.path.dirname(os.path.realpath(__file__))
root = sys.argv[sys.argv.index("--root") + 1]
subprocess.run(
    ["git", "-C", root, "commit", "-q", "--allow-empty", "-m", "chore: sneak one in"],
    check=True,
)
sys.exit(
    subprocess.run(
        [sys.executable, os.path.join(here, "real_update_loop.py"), *sys.argv[1:]]
    ).returncode
)
'''


class FinishCase(DetectPhaseCase):
    """Every task committed, a filled PASS report on disk, nothing else."""

    def setUp(self):
        super().setUp()
        with open(
            os.path.join(
                self.tmp.name, "skills", "tlc-spec-driven", "scripts", "check_commit.py"
            ),
            "w",
            encoding="utf-8",
        ) as fh:
            fh.write(CHECK_COMMIT_STUB)
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.write_validation(PASS_REPORT)

    # ---- fixture helpers -------------------------------------------------

    def head(self):
        return _git(self.root, "rev-parse", "HEAD").strip()

    def verified(self, **overrides):
        """The state a PASS round leaves behind: the verdict, stamped on HEAD."""
        verify = {
            "rounds": 1,
            "epoch_rounds": 1,
            "last_verdict": "PASS",
            "gaps_open": 0,
            "verified_at": self.head(),
        }
        verify.update(overrides)
        return self.write_state(verify=verify)

    def seal(self):
        """Commit the report the way the loop must: through the seal mode."""
        proc = subprocess.run(
            [
                sys.executable,
                os.path.join(self.skill_scripts, "checkpoint.py"),
                "demo",
                "--root",
                self.root,
                "--seal",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def finish(self, *args):
        return subprocess.run(
            [
                sys.executable,
                os.path.join(self.skill_scripts, "finish_loop.py"),
                "demo",
                "--root",
                self.root,
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def status(self):
        import json

        with open(self.state_path(), encoding="utf-8") as fh:
            return json.load(fh)["status"]

    def sealed_and_verified(self):
        """The full documented flow, up to the point `finish_loop.py` runs."""
        self.verified()
        self.seal()


class TheSignatureNeedsACoveredHead(FinishCase):
    """Scenario 7: a covered HEAD is the one situation that signs."""

    def test_a_sealed_pass_prints_the_signature(self):
        self.sealed_and_verified()
        proc = self.finish()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(SIGNATURE, proc.stdout)

    def test_the_signature_is_the_last_line(self):
        self.sealed_and_verified()
        proc = self.finish()
        self.assertEqual(proc.stdout.splitlines()[-1], SIGNATURE)

    def test_it_records_completion_through_the_single_writer(self):
        self.sealed_and_verified()
        self.finish()
        self.assertEqual(self.status(), "complete")

    def test_a_head_that_is_verified_at_itself_also_signs(self):
        # Coverage is `HEAD == verified_at` first and a seal second. Landing the
        # report by hand and verifying that tree is not the loop's flow, but it
        # is the simpler half of the rule and it has to hold on its own.
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "docs: land the report by hand")
        self.verified()
        proc = self.finish()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(SIGNATURE, proc.stdout)


class AStaleHeadIsRefused(FinishCase):
    """Scenario 6: `status=complete` never outranks the tree.

    This is the incident. The state said complete, the verdict said PASS, and
    two commits had landed since the verifier looked. Nothing in that sentence
    is a reason to print a success line.
    """

    def test_a_commit_after_the_pass_refuses_the_signature(self):
        verified_at = self.head()
        self.commit("docs: tweak the notes", "notes.txt")
        self.write_state(
            status="complete",
            verify={
                "rounds": 3,
                "epoch_rounds": 3,
                "last_verdict": "PASS",
                "gaps_open": 0,
                "verified_at": verified_at,
            },
        )
        proc = self.finish()
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("__TLC_LOOP__", proc.stdout)

    def test_the_refusal_names_the_phase_it_got(self):
        verified_at = self.head()
        self.commit("docs: tweak the notes", "notes.txt")
        self.write_state(
            verify={"rounds": 3, "epoch_rounds": 3, "last_verdict": "PASS",
                    "gaps_open": 0, "verified_at": verified_at}
        )
        proc = self.finish()
        self.assertIn("phase=V", proc.stderr)

    def test_a_recorded_halt_refuses_the_signature(self):
        # Scenario 9's other half: H is not a place a run signs from.
        self.sealed_and_verified()
        self.write_state(
            halt={"reason": "blast_radius", "detail": "push required"},
            status="halted",
            verify={"rounds": 1, "epoch_rounds": 1, "last_verdict": "PASS",
                    "gaps_open": 0, "verified_at": self.head()},
        )
        proc = self.finish()
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("__TLC_LOOP__", proc.stdout)

    def test_an_unsealed_report_leaves_the_tree_dirty_and_refuses(self):
        # The report is on disk and uncommitted. Signing here would claim a
        # verified tree while carrying a change no verifier ever saw.
        self.verified()
        proc = self.finish()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("validation.md", proc.stderr)

    def test_pending_work_refuses_the_signature(self):
        with open(os.path.join(self.feature_dir, "tasks.md"), encoding="utf-8") as fh:
            plan = fh.read()
        self.write_tasks(plan + "\n### T7: Seven\n**Tests**: unit\n**Gate**: quick\n")
        self.verified()
        proc = self.finish()
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("__TLC_LOOP__", proc.stdout)


class TheTreeMovingMidFlightIsRefused(FinishCase):
    """Scenario 8: a commit landing after the first check still refuses.

    Checking once and then acting is a race with the rest of the machine. The
    check is repeated after completion is recorded, against the HEAD read at the
    start, so a tree that moved in between cannot be signed for.
    """

    def setUp(self):
        super().setUp()
        copied = os.path.join(self.skill_scripts, "update_loop.py")
        os.replace(copied, os.path.join(self.skill_scripts, "real_update_loop.py"))
        with open(copied, "w", encoding="utf-8") as fh:
            fh.write(SNEAKY_UPDATE_STUB)

    def test_a_commit_during_the_recording_refuses_the_signature(self):
        self.sealed_and_verified()
        proc = self.finish()
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("__TLC_LOOP__", proc.stdout)

    def test_the_refusal_says_the_tree_moved(self):
        self.sealed_and_verified()
        proc = self.finish()
        self.assertIn("moved", proc.stderr.lower())


class PublishPreflight(FinishCase):
    """Scenario 11: publishing needs the base ref to be behind HEAD.

    Read-only, and outside the loop's authority to act on: it answers the
    question and stops. Push and PR creation stay a blast-radius decision.
    """

    def add_base(self, name="origin/main", ahead=False):
        """A ref standing in for the remote's base branch.

        The ahead case builds its commit on a detached HEAD with `--allow-empty`
        so no file is added or removed on the way through. A branch checkout
        that carried files would take the untracked `loop.json` with it.
        """
        if not ahead:
            _git(self.root, "update-ref", f"refs/remotes/{name}", "HEAD")
            return
        here = self.head()
        _git(self.root, "checkout", "-q", "--detach", f"{here}~1")
        _git(self.root, "commit", "-q", "--allow-empty", "-m", "chore: land upstream")
        _git(self.root, "update-ref", f"refs/remotes/{name}", "HEAD")
        _git(self.root, "checkout", "-q", "main")

    def test_a_base_that_is_an_ancestor_passes(self):
        self.add_base()
        self.sealed_and_verified()
        proc = self.finish("--preflight", "origin/main")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_a_base_that_moved_ahead_refuses(self):
        self.sealed_and_verified()
        self.add_base(ahead=True)
        proc = self.finish("--preflight", "origin/main")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("origin/main", proc.stderr)

    def test_the_refusal_names_the_way_out(self):
        self.sealed_and_verified()
        self.add_base(ahead=True)
        proc = self.finish("--preflight", "origin/main")
        for step in ("integrate", "verif", "seal", "finish"):
            self.assertIn(step, proc.stderr.lower())

    def test_it_never_prints_the_signature(self):
        self.add_base()
        self.sealed_and_verified()
        proc = self.finish("--preflight", "origin/main")
        self.assertNotIn("__TLC_LOOP__", proc.stdout)

    def test_it_writes_nothing(self):
        self.add_base()
        self.sealed_and_verified()
        with open(self.state_path(), "rb") as fh:
            before = fh.read()
        head_before = self.head()

        self.finish("--preflight", "origin/main")

        with open(self.state_path(), "rb") as fh:
            self.assertEqual(fh.read(), before)
        self.assertEqual(self.head(), head_before)

    def test_a_stale_head_refuses_before_the_base_is_even_read(self):
        self.add_base()
        verified_at = self.head()
        self.commit("docs: tweak", "notes.txt")
        self.write_state(
            verify={"rounds": 1, "epoch_rounds": 1, "last_verdict": "PASS",
                    "gaps_open": 0, "verified_at": verified_at}
        )
        proc = self.finish("--preflight", "origin/main")
        self.assertEqual(proc.returncode, 2)

    def test_an_unknown_base_ref_is_an_error_not_a_pass(self):
        self.sealed_and_verified()
        proc = self.finish("--preflight", "origin/nope")
        self.assertNotEqual(proc.returncode, 0)


class TheSignatureExistsInExactlyOnePlace(unittest.TestCase):
    """Scenario 15: no other script can emit the line.

    `loop.sh` breaks on `phase=E` and a goal evaluator matches the printed line.
    Both are downstream of whoever prints it, so the guarantee they rest on is
    that only the finalizer can. A grep is the whole enforcement.
    """

    def test_only_finish_loop_carries_the_signature(self):
        carriers = []
        for name in sorted(os.listdir(SCRIPTS)):
            if not name.endswith((".py", ".sh")) or name.startswith("test_"):
                continue
            with open(os.path.join(SCRIPTS, name), encoding="utf-8") as fh:
                if "__TLC_LOOP__" in fh.read():
                    carriers.append(name)
        self.assertEqual(carriers, ["finish_loop.py"])

    def test_loop_sh_does_not_print_it(self):
        with open(os.path.join(SCRIPTS, "loop.sh"), encoding="utf-8") as fh:
            self.assertNotIn("__TLC_LOOP__", fh.read())


if __name__ == "__main__":
    unittest.main()
