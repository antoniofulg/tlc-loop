"""Unit tests for detect_phase.py (T8, LOOP-01).

Derived from T8's "Done when" criteria and:
  - LOOP-01 AC 1: exactly one phase line describing the next action, printed
    before any work
  - LOOP-01 AC 2: completed tasks read from git trailers, authoritative over
    loop.json
  - LOOP-01 AC 3: an absent loop.json reconstructs from git and tasks.md
  - LOOP-01 AC 4: an unparseable loop.json halts with
    `phase=H reason=state_corrupt` rather than reconstructing (T28)
  - LOOP-04 AC 4: the configured verify-round limit reached without a PASS
    halts and escalates (T29)
  - LOOP-06 AC 6/7/8: halt on no progress, on a stuck gate, and on a
    configured iteration or minute limit

Each test builds a throwaway skill layout - this skill plus a sibling
`tlc-spec-driven` - and a separate tmpdir git repo, then runs the script as a
subprocess. The sibling's `validate_state.py` is a stub honouring its documented
contract (exit 0 only on a filled PASS report); the real validator is mutation
tested separately.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
FENCE = "```"

TASKS_MD = f"""# demo Tasks

## Test Coverage Matrix

## Gate Check Commands

## Execution Plan

### Phase 1: Foundation

{FENCE}
T1 -> T2 -> T3
{FENCE}

### Phase 2: Detection

{FENCE}
T4 -> T5 -> T6
{FENCE}

## Task Breakdown

### T1: One
**Tests**: unit
**Gate**: quick

### T2: Two
**Tests**: unit
**Gate**: quick

### T3: Three
**Tests**: unit
**Gate**: quick

### T4: Four
**Tests**: unit
**Gate**: quick

### T5: Five
**Tests**: unit
**Gate**: quick

### T6: Six
**Tests**: unit
**Gate**: quick
"""

# Honours validate_state.py's contract: a report must exist and hold a filled
# PASS verdict. Anything else is "not done".
VALIDATE_STATE_STUB = '''#!/usr/bin/env python3
import os, sys
feature = sys.argv[1]
root = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else "."
path = os.path.join(root, ".specs", "features", feature, "validation.md")
if not os.path.exists(path):
    sys.exit(1)
text = open(path, encoding="utf-8").read()
sys.exit(0 if "PASS" in text and "FAIL" not in text else 1)
'''


def _git(root, *args):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout


class DetectPhaseCase(unittest.TestCase):
    """Builds the skill layout and the project repo, then drives the script."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = self.tmp.name

        self.skill_scripts = os.path.join(base, "skills", "tlc-loop-tasks", "scripts")
        os.makedirs(self.skill_scripts)
        for name in os.listdir(SCRIPTS):
            if name.endswith(".py") and not name.startswith("test_"):
                shutil.copyfile(
                    os.path.join(SCRIPTS, name), os.path.join(self.skill_scripts, name)
                )

        tlc_scripts = os.path.join(base, "skills", "tlc-spec-driven", "scripts")
        os.makedirs(tlc_scripts)
        with open(os.path.join(tlc_scripts, "validate_state.py"), "w", encoding="utf-8") as fh:
            fh.write(VALIDATE_STATE_STUB)

        self.root = os.path.join(base, "project")
        self.feature_dir = os.path.join(self.root, ".specs", "features", "demo")
        os.makedirs(self.feature_dir)
        with open(os.path.join(self.feature_dir, "tasks.md"), "w", encoding="utf-8") as fh:
            fh.write(TASKS_MD)

        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "loop@test.invalid")
        _git(self.root, "config", "user.name", "Loop Test")
        _git(self.root, "config", "commit.gpgsign", "false")
        self.commit("chore: seed", "seed.txt")

    # ---- fixture helpers -------------------------------------------------

    def commit(self, message, filename, task=None):
        with open(os.path.join(self.root, filename), "w", encoding="utf-8") as fh:
            fh.write(filename)
        _git(self.root, "add", "-A")
        args = ["commit", "-q", "-m", message]
        if task:
            args += ["--trailer", f"Task: {task}", "--trailer", "Gate: quick PASS"]
        _git(self.root, *args)

    def complete(self, *task_ids):
        for task_id in task_ids:
            self.commit(f"feat: {task_id.lower()}", f"{task_id.lower()}.txt", task=task_id)

    def state_path(self):
        return os.path.join(self.feature_dir, "loop.json")

    def write_state(self, **overrides):
        sys.path.insert(0, SCRIPTS)
        import _state_io

        state = _state_io.new_state("demo", "ship demo", "claude")
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(state.get(key), dict):
                state[key].update(value)
            else:
                state[key] = value
        with open(self.state_path(), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        return state

    def write_config(self, text):
        specs = os.path.join(self.root, ".specs")
        os.makedirs(specs, exist_ok=True)
        with open(os.path.join(specs, "loop.config.toml"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def write_validation(self, text):
        with open(os.path.join(self.feature_dir, "validation.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    # ---- driver ----------------------------------------------------------

    def detect(self):
        return subprocess.run(
            [
                sys.executable,
                os.path.join(self.skill_scripts, "detect_phase.py"),
                "demo",
                "--root",
                self.root,
            ],
            capture_output=True,
            text=True,
        )

    def line(self):
        """Run, require exit 0 and exactly one stdout line, and return it."""
        proc = self.detect()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 1, f"expected exactly one line, got {lines!r}")
        return lines[0]


class Bootstrap(DetectPhaseCase):
    def test_absent_loop_json_prints_bootstrap(self):
        self.assertEqual(self.line(), "phase=0 action=bootstrap")

    def test_bootstrap_is_printed_even_before_any_commit_exists(self):
        self.assertFalse(os.path.exists(self.state_path()))
        self.assertEqual(self.line(), "phase=0 action=bootstrap")


class AbsentState(DetectPhaseCase):
    """T28 / LOOP-01 AC 3: an absent state file reconstructs, it does not halt."""

    def test_an_absent_state_file_does_not_halt(self):
        self.complete("T1", "T2", "T3")
        self.assertNotIn("phase=H", self.line())

    def test_deleting_the_state_file_costs_no_task_progress(self):
        # The spec's independent test: delete loop.json mid-feature and the
        # loop must still name the task git history implies. Bootstrap writes a
        # fresh state (no completed tasks in it), and the next detect
        # reconstructs the same answer from git plus tasks.md.
        self.write_state()
        self.complete("T1", "T2", "T3")
        before = self.line()
        self.assertEqual(before, "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6")

        os.unlink(self.state_path())
        self.assertEqual(self.line(), "phase=0 action=bootstrap")

        self.write_state()  # exactly what init_loop.py writes
        self.assertEqual(self.line(), before)


class ExecuteBatch(DetectPhaseCase):
    def test_pending_tasks_print_the_packed_batch_and_explicit_ids(self):
        self.write_state()
        self.assertEqual(
            self.line(),
            "phase=B action=execute_batch batch=P1+P2 tasks=T1,T2,T3,T4,T5,T6",
        )

    def test_the_batch_honours_the_configured_batch_size(self):
        self.write_state()
        self.write_config("[execute]\nbatch_size = 2\n")
        self.assertEqual(
            self.line(), "phase=B action=execute_batch batch=P1 tasks=T1,T2,T3"
        )

    def test_completed_tasks_come_from_git_trailers(self):
        self.write_state()
        self.complete("T1", "T2", "T3")
        self.assertEqual(
            self.line(), "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6"
        )

    def test_no_diff_tasks_are_unioned_with_the_git_trailers(self):
        self.write_state(no_diff_tasks=["T4"])
        self.complete("T1", "T2", "T3")
        self.assertEqual(self.line(), "phase=B action=execute_batch batch=P2 tasks=T5,T6")

    def test_git_wins_over_conflicting_state(self):
        # loop.json still claims T1 is the task in flight and T1..T3 are the
        # current batch; git says all three are committed, and git decides.
        self.write_state(current_task="T1", current_batch=["T1", "T2", "T3"])
        self.complete("T1", "T2", "T3")
        self.assertEqual(
            self.line(), "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6"
        )


class Reconciliation(DetectPhaseCase):
    """T31 / LOOP-01 AC 5: git overrides a `tasks.md` tick, and says so.

    `tasks.md` has no status field, so a human tick on a task header can claim
    a completion git never recorded. Git is the source of truth: the task stays
    pending. The disagreement rides the phase line so the orchestrator can
    record it through `update_loop.py`; this script must not write it itself.
    """

    def tick(self, *task_ids):
        """Re-write tasks.md with a completion tick on the named headers."""
        wanted = {task_id.upper() for task_id in task_ids}
        lines = []
        for line in TASKS_MD.splitlines():
            if line.startswith("### T") and line.split(":")[0][4:].upper() in wanted:
                line += " ✅"
            lines.append(line)
        with open(os.path.join(self.feature_dir, "tasks.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def test_a_tick_git_does_not_confirm_is_surfaced_on_the_line(self):
        self.write_state()
        self.tick("T1")
        self.assertEqual(
            self.line(),
            "phase=B action=execute_batch batch=P1+P2 "
            "tasks=T1,T2,T3,T4,T5,T6 reconciled=T1",
        )

    def test_every_disagreeing_task_is_named(self):
        self.write_state()
        self.tick("T1", "T4")
        self.assertTrue(self.line().endswith(" reconciled=T1,T4"), self.line())

    def test_the_ticked_task_is_still_dispatched_because_git_decides(self):
        # The point of the record: the plan says done, the loop runs it anyway.
        self.write_state()
        self.tick("T1")
        self.assertIn("tasks=T1,", self.line())

    def test_a_tick_git_confirms_is_no_disagreement(self):
        self.write_state()
        self.tick("T1")
        self.complete("T1")
        self.assertEqual(
            self.line(), "phase=B action=execute_batch batch=P1+P2 tasks=T2,T3,T4,T5,T6"
        )

    def test_an_unticked_plan_surfaces_nothing(self):
        self.write_state()
        self.complete("T1", "T2", "T3")
        self.assertEqual(
            self.line(), "phase=B action=execute_batch batch=P2 tasks=T4,T5,T6"
        )

    def test_a_no_diff_task_is_not_a_disagreement(self):
        # It carries no trailer by design, so a tick on it contradicts nothing.
        self.write_state(no_diff_tasks=["T4"])
        self.tick("T4")
        self.assertNotIn("reconciled=", self.line())

    def test_surfacing_the_disagreement_still_writes_nothing(self):
        self.write_state()
        self.tick("T1")
        with open(self.state_path(), "rb") as fh:
            state_before = fh.read()
        porcelain_before = _git(self.root, "status", "--porcelain")
        head_before = _git(self.root, "rev-parse", "HEAD")

        self.assertIn("reconciled=T1", self.line())

        with open(self.state_path(), "rb") as fh:
            self.assertEqual(fh.read(), state_before)
        self.assertEqual(_git(self.root, "status", "--porcelain"), porcelain_before)
        self.assertEqual(_git(self.root, "rev-parse", "HEAD"), head_before)

    def test_the_disagreement_never_costs_the_single_line_contract(self):
        self.write_state()
        self.tick("T1", "T2", "T3")
        proc = self.detect()
        self.assertEqual(len(proc.stdout.splitlines()), 1, proc.stdout)


class DuplicateTrailer(DetectPhaseCase):
    """T32 / LOOP-02 edge case: a duplicated `Task:` trailer is reported.

    A rebase or cherry-pick can leave the same trailer on two commits. The
    spec requires both halves: the task counts as completed exactly once, and
    the ambiguity is recorded rather than dropped.
    """

    def duplicate(self, task_id):
        """Land a further commit carrying the same `Task:` trailer."""
        self.copies = getattr(self, "copies", 0) + 1
        name = f"{task_id.lower()}-again-{self.copies}.txt"
        self.commit(f"fix: {task_id.lower()} again", name, task=task_id)

    def test_a_duplicated_trailer_is_surfaced_and_counted_once(self):
        self.write_state()
        self.complete("T1")
        self.duplicate("T1")
        self.assertEqual(
            self.line(),
            "phase=B action=execute_batch batch=P1+P2 tasks=T2,T3,T4,T5,T6 dup=T1",
        )

    def test_every_duplicated_task_is_named(self):
        self.write_state()
        self.complete("T1", "T2")
        self.duplicate("T1")
        self.duplicate("T2")
        self.assertTrue(self.line().endswith(" dup=T1,T2"), self.line())

    def test_a_task_duplicated_three_times_is_named_once(self):
        self.write_state()
        self.complete("T1")
        self.duplicate("T1")
        self.duplicate("T1")
        self.assertTrue(self.line().endswith(" dup=T1"), self.line())

    def test_a_clean_history_surfaces_nothing(self):
        self.write_state()
        self.complete("T1", "T2", "T3")
        self.assertNotIn("dup=", self.line())

    def test_the_ambiguity_is_reported_on_a_line_that_is_not_a_batch(self):
        # Duplication is a property of history, not of pending work, so it
        # outlives the last batch.
        self.write_state()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.duplicate("T3")
        self.assertEqual(self.line(), "phase=V action=verify round=1 dup=T3")

    def test_reporting_the_duplicate_writes_nothing(self):
        self.write_state()
        self.complete("T1")
        self.duplicate("T1")
        with open(self.state_path(), "rb") as fh:
            state_before = fh.read()
        porcelain_before = _git(self.root, "status", "--porcelain")
        head_before = _git(self.root, "rev-parse", "HEAD")

        self.assertIn("dup=T1", self.line())

        with open(self.state_path(), "rb") as fh:
            self.assertEqual(fh.read(), state_before)
        self.assertEqual(_git(self.root, "status", "--porcelain"), porcelain_before)
        self.assertEqual(_git(self.root, "rev-parse", "HEAD"), head_before)

    def test_both_advisory_fields_share_one_line_in_a_fixed_order(self):
        self.write_state()
        self.complete("T1")
        self.duplicate("T1")
        # T2 is ticked in the plan but never committed: two independent
        # observations, still exactly one line.
        lines = [
            line + " ✅" if line.startswith("### T2:") else line
            for line in TASKS_MD.splitlines()
        ]
        with open(os.path.join(self.feature_dir, "tasks.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        self.assertEqual(
            self.line(),
            "phase=B action=execute_batch batch=P1+P2 "
            "tasks=T2,T3,T4,T5,T6 reconciled=T2 dup=T1",
        )


class Verify(DetectPhaseCase):
    def test_no_pending_and_no_report_prints_verify_round_one(self):
        self.write_state()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.assertEqual(self.line(), "phase=V action=verify round=1")

    def test_the_round_number_follows_the_recorded_rounds(self):
        self.write_state(verify={"rounds": 2, "last_verdict": "FAIL", "gaps_open": 0})
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.assertEqual(self.line(), "phase=V action=verify round=3")

    def test_a_fail_verdict_with_no_open_gaps_returns_to_verify(self):
        self.write_state(verify={"rounds": 1, "last_verdict": "FAIL", "gaps_open": 0})
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.assertEqual(self.line(), "phase=V action=verify round=2")


class Fix(DetectPhaseCase):
    def test_a_fail_verdict_with_open_gaps_prints_fix(self):
        self.write_state(verify={"rounds": 1, "last_verdict": "FAIL", "gaps_open": 2})
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.assertEqual(self.line(), "phase=F action=fix round=1")


class VerifyCeiling(DetectPhaseCase):
    """T29 / LOOP-04 AC 4: the configured verify-round limit is a real halt.

    The ceiling is checked before a verify or a fix round is emitted, so an
    exhausted loop never dispatches another one. An omitted `max_rounds` is
    unlimited, the same TOML-has-no-null rule the `[limits]` keys follow.
    """

    def setUp(self):
        super().setUp()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")

    def test_below_the_limit_still_dispatches_a_verify_round(self):
        self.write_state(verify={"rounds": 2, "last_verdict": "FAIL", "gaps_open": 0})
        self.write_config("[verify]\nmax_rounds = 3\n")
        self.assertEqual(self.line(), "phase=V action=verify round=3")

    def test_reaching_the_limit_halts_with_verify_exhausted(self):
        self.write_state(verify={"rounds": 3, "last_verdict": "FAIL", "gaps_open": 0})
        self.write_config("[verify]\nmax_rounds = 3\n")
        line = self.line()
        self.assertTrue(
            line.startswith("phase=H action=halt reason=verify_exhausted "), line
        )

    def test_the_halt_detail_names_the_rounds_and_the_limit(self):
        self.write_state(verify={"rounds": 3, "last_verdict": "FAIL", "gaps_open": 0})
        self.write_config("[verify]\nmax_rounds = 3\n")
        line = self.line()
        self.assertIn("3", line)
        self.assertIn("max_rounds", line)

    def test_the_ceiling_is_checked_before_a_fix_round_is_emitted(self):
        # Open gaps would otherwise select phase=F, which would spend another
        # round on a loop that has already used its budget.
        self.write_state(verify={"rounds": 3, "last_verdict": "FAIL", "gaps_open": 2})
        self.write_config("[verify]\nmax_rounds = 3\n")
        line = self.line()
        self.assertNotIn("phase=F", line)
        self.assertIn("reason=verify_exhausted", line)

    def test_an_omitted_max_rounds_never_halts(self):
        self.write_state(verify={"rounds": 99, "last_verdict": "FAIL", "gaps_open": 0})
        self.assertEqual(self.line(), "phase=V action=verify round=100")

    def test_a_pass_report_closes_the_feature_even_at_the_ceiling(self):
        # "Reached without a PASS" is the condition. A PASS is not a halt.
        self.write_state(verify={"rounds": 3, "last_verdict": "PASS", "gaps_open": 0})
        self.write_config("[verify]\nmax_rounds = 3\n")
        self.write_validation("## Validation: demo - PASS\n\nEvidence: scripts/a.py:12\n")
        self.assertEqual(self.line(), "phase=E action=done")

    def test_pending_work_is_still_dispatched_at_the_ceiling(self):
        # The ceiling gates verify and fix rounds, not the batch that has not
        # run yet. T7 is planned and uncommitted, so there is work to do.
        with open(os.path.join(self.feature_dir, "tasks.md"), "a", encoding="utf-8") as fh:
            fh.write("\n### T7: Seven\n**Tests**: unit\n**Gate**: quick\n")
        self.write_state(verify={"rounds": 3, "last_verdict": "FAIL", "gaps_open": 2})
        self.write_config("[verify]\nmax_rounds = 3\n")
        self.assertEqual(self.line(), "phase=B action=execute_batch batch=P2 tasks=T7")


class Done(DetectPhaseCase):
    def test_validate_state_exiting_zero_prints_done(self):
        self.write_state()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.write_validation("## Validation: demo - PASS\n\nEvidence: scripts/a.py:12\n")
        self.assertEqual(self.line(), "phase=E action=done")

    def test_a_fail_report_does_not_print_done(self):
        self.write_state(verify={"rounds": 1, "last_verdict": "FAIL", "gaps_open": 1})
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.write_validation("## Validation: demo - FAIL\n\nEvidence: scripts/a.py:12\n")
        self.assertEqual(self.line(), "phase=F action=fix round=1")


class Halt(DetectPhaseCase):
    def test_a_recorded_halt_prints_its_reason_and_detail(self):
        self.write_state(halt={"reason": "blast_radius", "detail": "push required"})
        line = self.line()
        self.assertTrue(line.startswith("phase=H action=halt reason=blast_radius "), line)
        self.assertIn('detail="push required"', line)

    def test_halt_is_checked_before_any_work_is_described(self):
        # Pending tasks exist, so without the halt this would be phase=B.
        self.write_state(halt={"reason": "executor", "detail": "codex not installed"})
        self.assertNotIn("phase=B", self.line())
        self.assertIn("reason=executor", self.line())

    def test_no_progress_halts_at_the_configured_limit(self):
        self.write_state(counters={"iterations_without_commit": 3})
        self.write_config("[limits]\nno_progress_iterations = 3\n")
        self.assertIn("reason=no_progress", self.line())

    def test_gate_stuck_halts_past_the_configured_attempts(self):
        self.write_state(counters={"gate_attempts": {"T4": 4}})
        self.write_config("[limits]\ngate_attempts_per_task = 3\n")
        line = self.line()
        self.assertIn("reason=gate_stuck", line)
        self.assertIn("T4", line)

    def test_max_iterations_halts_with_the_limit_reason(self):
        self.write_state(iteration=200)
        self.write_config("[limits]\nmax_iterations = 200\n")
        self.assertIn("reason=limit", self.line())

    def test_a_blocked_status_halts(self):
        self.write_state(status="blocked")
        self.assertIn("reason=blocker", self.line())

    def test_an_omitted_limit_never_halts(self):
        # TOML has no null: with no [limits] table every limit is unlimited,
        # so these counters must not stop the run.
        self.write_state(
            iteration=9999,
            counters={"iterations_without_commit": 99, "gate_attempts": {"T4": 42}},
        )
        self.assertTrue(self.line().startswith("phase=B "), self.line())


class ReadOnly(DetectPhaseCase):
    def test_a_run_writes_nothing(self):
        self.write_state(current_task="T1")
        self.complete("T1", "T2")
        with open(self.state_path(), "rb") as fh:
            state_before = fh.read()
        porcelain_before = _git(self.root, "status", "--porcelain")
        head_before = _git(self.root, "rev-parse", "HEAD")

        self.assertTrue(self.line().startswith("phase=B "))

        with open(self.state_path(), "rb") as fh:
            self.assertEqual(fh.read(), state_before)
        self.assertEqual(_git(self.root, "status", "--porcelain"), porcelain_before)
        self.assertEqual(_git(self.root, "rev-parse", "HEAD"), head_before)

    def test_repeated_runs_print_the_same_line(self):
        self.write_state()
        self.complete("T1")
        self.assertEqual(self.line(), self.line())


class CorruptState(DetectPhaseCase):
    """T28 / LOOP-01 AC 4: unreadable state halts in the phase vocabulary.

    An existing `loop.json` the codec cannot read is not a script failure, it
    is a situation: it is reported as `phase=H reason=state_corrupt` so every
    consumer of the contract reads one vocabulary instead of special-casing a
    raw exit code. Reconstructing instead would silently discard the immutable
    objective.
    """

    def corrupt(self, text="{ not json"):
        with open(self.state_path(), "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_malformed_loop_json_halts_with_state_corrupt(self):
        self.corrupt()
        self.assertTrue(
            self.line().startswith("phase=H action=halt reason=state_corrupt "), self.line()
        )

    def test_the_parse_error_travels_as_the_detail(self):
        self.corrupt()
        line = self.line()
        self.assertIn("malformed JSON", line)
        self.assertIn('detail="', line)

    def test_the_halt_exits_zero_with_nothing_on_stderr(self):
        self.corrupt()
        proc = self.detect()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")

    def test_a_schema_violation_halts_with_the_same_reason(self):
        self.write_state(status="sleepy")
        line = self.line()
        self.assertTrue(
            line.startswith("phase=H action=halt reason=state_corrupt "), line
        )
        self.assertIn("sleepy", line)

    def test_corrupt_state_is_never_reconstructed_into_work(self):
        # T1..T6 are all pending, so without the halt this would be phase=B.
        self.corrupt()
        self.assertNotIn("phase=B", self.line())


class ErrorPaths(DetectPhaseCase):
    def test_a_missing_tasks_md_exits_one_naming_the_path(self):
        self.write_state()
        os.unlink(os.path.join(self.feature_dir, "tasks.md"))
        proc = self.detect()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("tasks.md", proc.stderr)

    def test_a_malformed_config_exits_one(self):
        self.write_state()
        self.write_config("[limits\nmax_iterations = 1\n")
        proc = self.detect()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("loop.config.toml", proc.stderr)


if __name__ == "__main__":
    unittest.main()
