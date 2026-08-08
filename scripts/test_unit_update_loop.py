"""Unit tests for update_loop.py (T10, LOOP-06).

Derived from T10's "Done when" criteria and:
  - LOOP-01 AC 6: `loop.json` is mutated only through its own state-writing
    script
  - LOOP-06 AC 5: the objective recorded at bootstrap stays immutable for the
    remainder of the run (D12)
  - LOOP-06 AC 6: no new commit across the configured number of iterations is
    what the no-progress halt counts
  - LOOP-06 AC 7: the same task's gate failing more than the configured number
    of attempts is what the gate-stuck halt counts

The counters asserted here are the ones `detect_phase.halt_reason` reads, so a
counter written under the wrong key would leave a halt condition that can never
fire. Each test runs the script as a subprocess against a state file in its own
TemporaryDirectory.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

import _state_io  # noqa: E402

FEATURE = "demo"
OBJECTIVE = "ship demo end to end"


def _seed(root, **overrides):
    """Write a bootstrap-shaped state file, with optional field overrides."""
    os.makedirs(os.path.join(root, ".specs", "features", FEATURE), exist_ok=True)
    state = _state_io.new_state(FEATURE, OBJECTIVE, "claude")
    state.update(overrides)
    _state_io.save(FEATURE, root, state)
    return state


def _git(root, *args):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout


def _seed_repo(root):
    """Make `root` a repo with one commit, and return its SHA."""
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "loop@test.invalid")
    _git(root, "config", "user.name", "Loop Test")
    _git(root, "config", "commit.gpgsign", "false")
    return _commit_more(root, "seed.txt", "chore: seed")


def _commit_more(root, filename="more.txt", message="chore: more"):
    with open(os.path.join(root, filename), "w", encoding="utf-8") as fh:
        fh.write(filename)
    _git(root, "add", filename)
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD").strip()


def _read(root):
    with open(_state_io.state_path(FEATURE, root), encoding="utf-8") as fh:
        return json.load(fh)


def _run(root, *args):
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "update_loop.py"), FEATURE, "--root", root, *args],
        capture_output=True,
        text=True,
    )


class IterationIncrement(unittest.TestCase):
    """`--iteration-done` increments `iteration` exactly once per invocation."""

    def test_one_invocation_increments_by_exactly_one(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            proc = _run(root, "--iteration-done", "--phase", "B", "--action", "batch")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(_read(root)["iteration"], 1)

    def test_three_invocations_increment_by_exactly_three(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            for _ in range(3):
                self.assertEqual(_run(root, "--iteration-done").returncode, 0)
            self.assertEqual(_read(root)["iteration"], 3)

    def test_a_mutation_without_iteration_done_leaves_iteration_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root, iteration=4)
            self.assertEqual(_run(root, "--task-started", "T2").returncode, 0)
            self.assertEqual(_read(root)["iteration"], 4)


class IterationLog(unittest.TestCase):
    """`iterations[]` is append-only and capped at the last 50 entries."""

    def test_an_entry_is_appended_after_the_existing_ones(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root, iterations=[{"n": 1, "action": "older"}])
            _run(root, "--iteration-done", "--phase", "B", "--action", "newer")
            log = _read(root)["iterations"]
            self.assertEqual(len(log), 2)
            self.assertEqual(log[0]["action"], "older")
            self.assertEqual(log[1]["action"], "newer")

    def test_the_entry_records_the_phase_and_action_it_was_given(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--iteration-done", "--phase", "V", "--action", "verify round 1")
            entry = _read(root)["iterations"][-1]
            self.assertEqual(entry["phase"], "V")
            self.assertEqual(entry["action"], "verify round 1")
            self.assertEqual(entry["n"], 1)

    def test_the_log_is_capped_at_the_last_fifty_entries(self):
        with tempfile.TemporaryDirectory() as root:
            seeded = [{"n": i, "action": f"seed{i}"} for i in range(49)]
            _seed(root, iterations=seeded)
            for i in range(3):
                _run(root, "--iteration-done", "--action", f"new{i}")
            log = _read(root)["iterations"]
            self.assertEqual(len(log), 50)
            # the three oldest seeded entries fell off the front, newest kept
            self.assertEqual(log[0]["action"], "seed2")
            self.assertEqual(log[-1]["action"], "new2")

    def test_an_overlong_existing_log_is_trimmed_to_the_last_fifty(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root, iterations=[{"n": i, "action": f"seed{i}"} for i in range(60)])
            _run(root, "--iteration-done", "--action", "newest")
            log = _read(root)["iterations"]
            self.assertEqual(len(log), 50)
            self.assertEqual(log[-1]["action"], "newest")


class ObjectiveIsImmutable(unittest.TestCase):
    """A write targeting `objective` is rejected with a non-zero exit (D12)."""

    def test_targeting_objective_exits_non_zero(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            proc = _run(root, "--objective", "something else")
            self.assertNotEqual(proc.returncode, 0)

    def test_the_rejection_names_the_field(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            proc = _run(root, "--objective", "something else")
            self.assertIn("objective", proc.stderr.lower())

    def test_the_stored_objective_is_unchanged_by_the_rejected_call(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--objective", "something else")
            self.assertEqual(_read(root)["objective"], OBJECTIVE)

    def test_a_rejected_call_applies_none_of_its_other_flags(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--iteration-done", "--objective", "something else")
            self.assertEqual(_read(root)["iteration"], 0)

    def test_an_ordinary_update_leaves_the_objective_intact(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--iteration-done", "--phase", "B", "--action", "work")
            self.assertEqual(_read(root)["objective"], OBJECTIVE)


class GateAttemptCounter(unittest.TestCase):
    """`--gate-attempt` feeds the counter the gate_stuck halt reads."""

    def test_the_first_attempt_records_one_for_that_task(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertEqual(_run(root, "--gate-attempt", "T3").returncode, 0)
            self.assertEqual(_read(root)["counters"]["gate_attempts"], {"T3": 1})

    def test_repeated_attempts_accumulate_per_task(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--gate-attempt", "T3")
            _run(root, "--gate-attempt", "T3")
            _run(root, "--gate-attempt", "T4")
            self.assertEqual(_read(root)["counters"]["gate_attempts"], {"T3": 2, "T4": 1})


class IterationsWithoutCommit(unittest.TestCase):
    """Resets on a recorded commit, increments otherwise (LOOP-06 AC 6)."""

    def test_it_increments_when_the_iteration_records_no_commit(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--iteration-done")
            self.assertEqual(_read(root)["counters"]["iterations_without_commit"], 1)
            _run(root, "--iteration-done")
            self.assertEqual(_read(root)["counters"]["iterations_without_commit"], 2)

    def test_it_resets_to_zero_when_a_commit_is_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            state = _state_io.new_state(FEATURE, OBJECTIVE, "claude")
            state["counters"]["iterations_without_commit"] = 2
            os.makedirs(os.path.join(root, ".specs", "features", FEATURE), exist_ok=True)
            _state_io.save(FEATURE, root, state)
            _run(root, "--iteration-done", "--commit", "abc1234")
            self.assertEqual(_read(root)["counters"]["iterations_without_commit"], 0)

    def test_the_recorded_commit_appears_in_the_iteration_entry(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--iteration-done", "--commit", "abc1234")
            self.assertEqual(_read(root)["iterations"][-1]["commit"], "abc1234")


class TaskTracking(unittest.TestCase):
    def test_task_started_records_the_current_task(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--task-started", "T5")
            self.assertEqual(_read(root)["current_task"], "T5")

    def test_task_done_clears_the_current_task(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root, current_task="T5")
            _run(root, "--task-done", "T5")
            self.assertIsNone(_read(root)["current_task"])

    def test_a_no_diff_task_is_recorded_so_detect_phase_can_union_it(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertEqual(_run(root, "--task-done", "T4", "--no-diff").returncode, 0)
            self.assertEqual(_read(root)["no_diff_tasks"], ["T4"])

    def test_a_task_with_a_diff_is_not_recorded_as_no_diff(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--task-done", "T4", "--commit", "abc1234")
            self.assertEqual(_read(root)["no_diff_tasks"], [])

    def test_no_diff_without_a_task_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertNotEqual(_run(root, "--no-diff", "--iteration-done").returncode, 0)

    def test_the_batch_is_recorded_as_a_list_of_task_ids(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--batch", "T1,T2,T3")
            self.assertEqual(_read(root)["current_batch"], ["T1", "T2", "T3"])


class ReconciliationRecord(unittest.TestCase):
    """T31 / LOOP-01 AC 5: git overriding a `tasks.md` tick is recorded.

    `detect_phase.py` finds the disagreement and prints it; it cannot write,
    so this script is the half that makes the record durable. The entry names
    the task and the side that won, which is what lets a later reader tell why
    a task the plan calls finished was dispatched again.
    """

    def test_a_disagreement_is_recorded_with_the_task_and_the_winning_side(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertEqual(_run(root, "--reconciled", "T4").returncode, 0)
            entries = _read(root)["reconciled"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["task"], "T4")
            self.assertEqual(entries[0]["winner"], "git")
            self.assertRegex(entries[0]["at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_several_ids_in_one_call_are_each_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--reconciled", "T4,T5")
            self.assertEqual(
                [e["task"] for e in _read(root)["reconciled"]], ["T4", "T5"]
            )

    def test_recording_the_same_reconciliation_twice_does_not_duplicate_it(self):
        # Detection re-derives the disagreement every iteration, so the same
        # ids arrive over and over until the tick or the history is fixed.
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--reconciled", "T4")
            _run(root, "--reconciled", "T4,T5")
            _run(root, "--reconciled", "T4")
            self.assertEqual(
                [e["task"] for e in _read(root)["reconciled"]], ["T4", "T5"]
            )

    def test_an_unrelated_update_leaves_the_record_alone(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--reconciled", "T4")
            _run(root, "--iteration-done", "--phase", "B")
            self.assertEqual([e["task"] for e in _read(root)["reconciled"]], ["T4"])

    def test_reconciled_alone_is_a_real_action_not_a_no_op(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            proc = _run(root, "--reconciled", "T4")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("nothing to do", proc.stderr)


class VerifyRounds(unittest.TestCase):
    """`--verify-round` feeds the fields detect_phase reads for phase V and F."""

    def test_a_round_increments_the_count_and_records_the_verdict(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--verify-round", "FAIL")
            verify = _read(root)["verify"]
            self.assertEqual(verify["rounds"], 1)
            self.assertEqual(verify["last_verdict"], "FAIL")

    def test_open_gaps_are_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--verify-round", "FAIL", "--gaps", "2")
            self.assertEqual(_read(root)["verify"]["gaps_open"], 2)

    def test_a_pass_round_records_the_report_path(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--verify-round", "PASS", "--report", ".specs/f/validation.md")
            verify = _read(root)["verify"]
            self.assertEqual(verify["last_verdict"], "PASS")
            self.assertEqual(verify["last_report"], ".specs/f/validation.md")

    def test_a_round_stamps_the_commit_it_covered(self):
        # Without this, detect_phase cannot tell a current PASS from one the
        # code has moved past, which is the whole of T34.
        with tempfile.TemporaryDirectory() as root:
            head = _seed_repo(root)
            _seed(root)
            _run(root, "--verify-round", "PASS")
            self.assertEqual(_read(root)["verify"]["verified_at"], head)

    def test_the_stamp_tracks_head_rather_than_a_fixed_value(self):
        # A stamp that is merely present, or always the same, would satisfy a
        # weaker assertion while accepting every stale report.
        with tempfile.TemporaryDirectory() as root:
            first = _seed_repo(root)
            _seed(root)
            _run(root, "--verify-round", "FAIL")
            self.assertEqual(_read(root)["verify"]["verified_at"], first)
            second = _commit_more(root)
            self.assertNotEqual(first, second)
            _run(root, "--verify-round", "PASS")
            self.assertEqual(_read(root)["verify"]["verified_at"], second)

    def test_outside_a_repository_the_stamp_is_absent_rather_than_wrong(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--verify-round", "PASS")
            self.assertIsNone(_read(root)["verify"]["verified_at"])

    def test_an_unknown_verdict_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertNotEqual(_run(root, "--verify-round", "MAYBE").returncode, 0)


class HaltRecording(unittest.TestCase):
    def test_a_halt_records_the_reason_and_detail_detect_phase_prints(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--halt", "executor", "--detail", "codex quota exhausted")
            halt = _read(root)["halt"]
            self.assertEqual(halt["reason"], "executor")
            self.assertEqual(halt["detail"], "codex quota exhausted")

    def test_a_halt_moves_the_run_out_of_active(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--halt", "limit")
            self.assertEqual(_read(root)["status"], "halted")

    def test_an_unknown_halt_reason_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertNotEqual(_run(root, "--halt", "because_i_said_so").returncode, 0)

    def test_an_explicit_status_wins_over_the_halt_default(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(root, "--halt", "blocker", "--status", "blocked")
            self.assertEqual(_read(root)["status"], "blocked")


class Failures(unittest.TestCase):
    def test_a_missing_state_file_exits_non_zero_naming_the_path(self):
        with tempfile.TemporaryDirectory() as root:
            proc = _run(root, "--iteration-done")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("loop.json", proc.stderr)

    def test_an_unparseable_state_file_exits_non_zero(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".specs", "features", FEATURE))
            with open(_state_io.state_path(FEATURE, root), "w", encoding="utf-8") as fh:
                fh.write("{not json")
            self.assertNotEqual(_run(root, "--iteration-done").returncode, 0)

    def test_an_invocation_with_no_action_exits_non_zero(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertNotEqual(_run(root).returncode, 0)


class WrittenStateStaysValid(unittest.TestCase):
    """Every write goes through the codec, so the file stays loadable."""

    def test_the_state_still_loads_after_a_full_update(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            _run(
                root,
                "--iteration-done",
                "--phase", "B",
                "--action", "batch P1",
                "--batch", "T1,T2",
                "--task-done", "T1",
                "--commit", "abc1234",
                "--gate-attempt", "T1",
            )
            state = _state_io.load(FEATURE, root)
            self.assertEqual(state["iteration"], 1)
            self.assertEqual(state["current_batch"], ["T1", "T2"])

    def test_last_updated_advances_on_a_write(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root, last_updated="2000-01-01T00:00:00Z")
            _run(root, "--iteration-done")
            self.assertNotEqual(_read(root)["last_updated"], "2000-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
