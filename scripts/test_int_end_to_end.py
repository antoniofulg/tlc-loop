"""End-to-end run of the loop over a toy feature (T27, LOOP-01).

Everything phases 1 to 6 built, driven together over one real git repository in
a tmpdir: bootstrap writes state, detection names a batch, `checkpoint.py`
records tasks as commit trailers, detection advances on those trailers alone,
deleting `loop.json` re-bootstraps without re-dispatching a finished task, and
`loop.sh` stops on both terminals.

The sibling validators are the real ones - `validate_tasks.py` gates the
bootstrap, `check_commit.py` gates every message, `validate_state.py` decides
`phase=E`. Stubbing them would leave the integration untested at exactly the
seams where it can break. The whole module skips when the sibling skill is not
installed.

**No executor runs here.** The only stub is the stage resolver, and it records
every call so the tests can prove it was never reached. Nothing spawns a
provider CLI and nothing touches the network: the subprocesses are `git`, this
interpreter, and `bash` running `loop.sh`.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

from test_int_tlc_validators import sibling_script  # noqa: E402

LOOP_SH = os.path.join(SCRIPTS, "loop.sh")

#: The sibling scripts this run actually reaches.
SIBLING_SCRIPTS = ("validate_tasks.py", "check_commit.py", "validate_state.py")

FENCE = "```"

#: Three phases of two tasks. With `batch_size = 2` the first batch is Phase 1
#: alone, and the rest fold into one - a two-batch feature, which is what makes
#: the advance observable.
TASKS_MD = f"""# toy Tasks

## Test Coverage Matrix

| Code Layer | Required Test Type |
| --- | --- |
| everything | unit |

## Gate Check Commands

| Gate Level | Command |
| --- | --- |
| Quick | `true` |

## Execution Plan

### Phase 1: Foundation

{FENCE}
T1 -> T2
{FENCE}

### Phase 2: Wiring

{FENCE}
T3 -> T4
{FENCE}

### Phase 3: Polish

{FENCE}
T5 -> T6
{FENCE}

## Task Breakdown

### T1: One
**Where**: `src/one.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

### T2: Two
**Where**: `src/two.py`
**Depends on**: T1
**Tests**: unit
**Gate**: quick

### T3: Three
**Where**: `src/three.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

### T4: Four
**Where**: `src/four.py`
**Depends on**: T3
**Tests**: unit
**Gate**: quick

### T5: Five
**Where**: `src/five.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

### T6: Six
**Where**: `src/six.py`
**Depends on**: T5
**Tests**: unit
**Gate**: quick
"""

STAGED_TASKS_MD = (
    TASKS_MD.replace(
        "### Phase 1: Foundation\n\n",
        "### Phase 1: Foundation\n\n**Stage:** foundation\n\n",
    )
    .replace(
        "### Phase 2: Wiring\n\n",
        "### Phase 2: Backend wiring\n\n**Stage:** backend\n\n",
    )
    .replace(
        f"### Phase 3: Polish\n\n{FENCE}\nT5 -> T6\n{FENCE}",
        f"""### Phase 3: Frontend polish

**Stage:** frontend

{FENCE}
T5
{FENCE}

### Phase 4: Documentation

**Stage:** docs

{FENCE}
T6
{FENCE}""",
    )
)

#: The file each task's `Where` field names in TASKS_MD above.
TASK_FILES = {
    "T1": "one",
    "T2": "two",
    "T3": "three",
    "T4": "four",
    "T5": "five",
    "T6": "six",
}

PASS_REPORT = """## Validation: toy - PASS

Per-AC evidence: `src/one.py:1` implements LOOP-01 AC 1.
"""

#: The second report. A re-verification after a merge covers a different diff
#: range, so it is a different file - which is also what makes it sealable.
SECOND_PASS_REPORT = """## Validation: toy - PASS

Per-AC evidence: `src/six.py:1` implements LOOP-01 AC 1 after the base merge.
"""

#: Stands in for `resolve_stage.py`. It appends to a marker file on every call,
#: which is how the tests prove no executor was ever resolved, let alone run.
RESOLVE_STUB = '''#!/usr/bin/env python3
import os, sys

with open(os.environ["STUB_RESOLVE_CALLS"], "a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\\n")
sys.stdout.write("kind=command provider=stub cmd=/usr/bin/true\\n")
'''

OBJECTIVE = "ship the toy feature end to end"


def _git(root, *args, check=True):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Resolves the sibling or skips the whole module with the paths tried.
        cls.sibling_dir = os.path.dirname(sibling_script(SIBLING_SCRIPTS[0]))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = self.tmp.name

        # 1. The two skills, side by side, exactly as _paths expects them.
        self.skill_scripts = os.path.join(base, "skills", "tlc-loop", "scripts")
        os.makedirs(self.skill_scripts)
        for name in os.listdir(SCRIPTS):
            if name.endswith(".py") and not name.startswith("test_"):
                shutil.copyfile(
                    os.path.join(SCRIPTS, name), os.path.join(self.skill_scripts, name)
                )

        tlc_scripts = os.path.join(base, "skills", "tlc-spec-driven", "scripts")
        os.makedirs(tlc_scripts)
        for name in SIBLING_SCRIPTS:
            shutil.copyfile(sibling_script(name), os.path.join(tlc_scripts, name))

        # 2. The project: a real repository carrying a valid plan.
        self.root = os.path.join(base, "project")
        self.feature_dir = os.path.join(self.root, ".specs", "features", "toy")
        os.makedirs(self.feature_dir)
        self.write(".specs/features/toy/tasks.md", TASKS_MD)
        shutil.copyfile(
            os.path.join(os.path.dirname(SCRIPTS), ".gitignore"),
            os.path.join(self.root, ".gitignore"),
        )

        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "loop@test.invalid")
        _git(self.root, "config", "user.name", "Loop Test")
        _git(self.root, "config", "commit.gpgsign", "false")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "chore: seed the toy project")

        self.resolve_calls = os.path.join(base, "resolve_calls.txt")
        self.resolve_stub = os.path.join(base, "stub_resolve.py")
        with open(self.resolve_stub, "w", encoding="utf-8") as fh:
            fh.write(RESOLVE_STUB)
        os.chmod(self.resolve_stub, 0o755)

    # ---- fixture helpers -------------------------------------------------

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def script(self, name):
        return os.path.join(self.skill_scripts, name)

    def run_script(self, name, *args):
        return subprocess.run(
            [sys.executable, self.script(name), *args], capture_output=True, text=True
        )

    def state_path(self):
        return os.path.join(self.feature_dir, "loop.json")

    def state_bytes(self):
        with open(self.state_path(), "rb") as fh:
            return fh.read()

    def bootstrap(self):
        proc = self.run_script(
            "init_loop.py", "toy", "--root", self.root,
            "--objective", OBJECTIVE, "--respawn", "claude",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def detect(self):
        proc = self.run_script("detect_phase.py", "toy", "--root", self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 1, f"expected exactly one line, got {lines!r}")
        return lines[0]

    def do_task(self, task_id):
        """Write the task's file and checkpoint it, the way a batch worker's
        output is committed: the orchestrator commits, never the executor.

        The file is the one the task's `Where` field names, so the commit
        contents match the plan instead of an invented path.
        """
        name = TASK_FILES[task_id]
        self.write(f"src/{name}.py", f"# {task_id}\n")
        proc = self.run_script(
            "checkpoint.py", "toy", "--root", self.root,
            "--task", task_id, "--gate", "quick", "--gate-result", "PASS",
            "--message", f"feat(toy): add {name}",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def complete(self, *task_ids):
        for task_id in task_ids:
            self.do_task(task_id)

    def write_config(self, text):
        self.write(".specs/loop.config.toml", text)

    def run_loop_sh(self):
        env = dict(
            os.environ,
            LOOP_DETECT_CMD=f"{sys.executable} {self.script('detect_phase.py')}",
            LOOP_RESOLVE_CMD=f"{sys.executable} {self.resolve_stub}",
            STUB_RESOLVE_CALLS=self.resolve_calls,
        )
        return subprocess.run(
            ["bash", LOOP_SH, "toy", "--root", self.root],
            capture_output=True, text=True, env=env, timeout=120,
        )

    def assert_no_executor_ran(self):
        self.assertFalse(
            os.path.exists(self.resolve_calls),
            "a stage was resolved, so the driver tried to spawn an executor",
        )

    # ---- 1. bootstrap ----------------------------------------------------

    def test_the_plan_passes_the_real_sibling_gate(self):
        proc = subprocess.run(
            [sys.executable, sibling_script("validate_tasks.py"), "toy", "--root", self.root],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_an_unbootstrapped_feature_asks_to_bootstrap(self):
        self.assertEqual(self.detect(), "phase=0 action=bootstrap")

    def test_bootstrap_then_detect_names_the_first_batch(self):
        self.write_config("[execute]\nbatch_size = 2\n")
        self.bootstrap()
        self.assertTrue(os.path.isfile(self.state_path()))
        self.assertEqual(
            self.detect(),
            "phase=B action=execute_batch batch=P1 tasks=T1,T2 stage=implement",
        )

    def test_four_domain_stages_route_as_four_ordered_batches(self):
        self.write(".specs/features/toy/tasks.md", STAGED_TASKS_MD)
        self.write_config(
            '[stages.foundation]\nprovider = "auto"\n'
            '[stages.backend]\nprovider = "auto"\n'
            '[stages.frontend]\nprovider = "auto"\n'
            '[stages.docs]\nprovider = "auto"\n'
            '[execute]\nstrict_routing = true\nbatch_size = 7\n'
        )
        bootstrapped = self.bootstrap()
        for expected in (
            "Phase 1: Foundation -> foundation (claude/-)",
            "Phase 2: Backend wiring -> backend (claude/-)",
            "Phase 3: Frontend polish -> frontend (claude/-)",
            "Phase 4: Documentation -> docs (claude/-)",
        ):
            self.assertIn(expected, bootstrapped.stdout)

        expected_batches = (
            ("phase=B action=execute_batch batch=P1 tasks=T1,T2 stage=foundation", ("T1", "T2")),
            ("phase=B action=execute_batch batch=P2 tasks=T3,T4 stage=backend", ("T3", "T4")),
            ("phase=B action=execute_batch batch=P3 tasks=T5 stage=frontend", ("T5",)),
            ("phase=B action=execute_batch batch=P4 tasks=T6 stage=docs", ("T6",)),
        )
        for line, tasks in expected_batches:
            self.assertEqual(self.detect(), line)
            self.complete(*tasks)
        self.assertEqual(self.detect(), "phase=V action=verify round=1")

    # ---- 2. trailers advance the phase ----------------------------------

    def test_trailered_commits_advance_the_detected_phase(self):
        self.write_config("[execute]\nbatch_size = 2\n")
        self.bootstrap()
        self.complete("T1", "T2")
        self.assertEqual(
            self.detect(),
            "phase=B action=execute_batch batch=P2+P3 "
            "tasks=T3,T4,T5,T6 stage=implement",
        )

    def test_the_advance_is_carried_by_the_task_trailers(self):
        self.bootstrap()
        self.complete("T1", "T2")
        trailers = _git(
            self.root, "log", "--reverse", "--format=%(trailers:key=Task,valueonly)"
        ).stdout.split()
        self.assertEqual(trailers, ["T1", "T2"])

    def test_the_advance_writes_no_state(self):
        self.write_config("[execute]\nbatch_size = 2\n")
        self.bootstrap()
        before = self.state_bytes()
        self.detect()
        self.complete("T1", "T2")
        self.detect()
        self.assertEqual(self.state_bytes(), before)

    def test_no_task_commit_carries_the_state_file(self):
        self.bootstrap()
        self.complete("T1")
        files = _git(self.root, "show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertIn("src/one.py", files)
        self.assertNotIn(".specs/features/toy/loop.json", files)

    # ---- 3. resume after losing the state file ---------------------------

    def test_deleting_loop_json_mid_run_yields_the_same_next_task(self):
        self.write_config("[execute]\nbatch_size = 2\n")
        self.bootstrap()
        self.complete("T1", "T2")
        before = self.detect()
        self.assertEqual(
            before,
            "phase=B action=execute_batch batch=P2+P3 "
            "tasks=T3,T4,T5,T6 stage=implement",
        )

        os.unlink(self.state_path())
        self.assertEqual(self.detect(), "phase=0 action=bootstrap")

        self.bootstrap()
        self.assertEqual(self.detect(), before)

    def test_the_rebuilt_state_starts_from_zero_and_keeps_the_objective(self):
        import json

        self.bootstrap()
        self.complete("T1", "T2")
        os.unlink(self.state_path())
        self.bootstrap()
        with open(self.state_path(), encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["objective"], OBJECTIVE)
        self.assertEqual(state["iteration"], 0)

    # ---- 4. halt stops the loop ------------------------------------------

    def test_a_halt_condition_is_reported_with_its_reason(self):
        self.bootstrap()
        self.write_config("[limits]\nno_progress_iterations = 1\n")
        closed = self.run_script(
            "update_loop.py", "toy", "--root", self.root,
            "--iteration-done", "--phase", "B", "--action", "batch 1",
        )
        self.assertEqual(closed.returncode, 0, closed.stderr)
        line = self.detect()
        self.assertTrue(line.startswith("phase=H action=halt reason=no_progress "), line)

    def test_the_driver_stops_on_the_halt_instead_of_respawning(self):
        self.bootstrap()
        self.write_config("[limits]\nno_progress_iterations = 1\n")
        self.run_script(
            "update_loop.py", "toy", "--root", self.root,
            "--iteration-done", "--phase", "B", "--action", "batch 1",
        )
        proc = self.run_loop_sh()
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("reason=no_progress", proc.stdout.splitlines()[-1])
        self.assert_no_executor_ran()

    # ---- 5. the terminal path --------------------------------------------

    def test_every_task_done_asks_for_verification(self):
        self.bootstrap()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.assertEqual(self.detect(), "phase=V action=verify round=1")

    def record_pass(self):
        """Write the report and record the verdict the way the loop does.

        A PASS closes the feature only while it still covers HEAD, so the
        verdict has to be recorded through the writer that stamps the commit -
        writing the report alone leaves nothing on record (T34).
        """
        self.write(".specs/features/toy/validation.md", PASS_REPORT)
        recorded = self.run_script(
            "update_loop.py", "toy", "--root", self.root,
            "--verify-round", "PASS", "--gaps", "0",
            "--report", ".specs/features/toy/validation.md",
            "--iteration-done", "--phase", "V", "--action", "verify round 1",
        )
        self.assertEqual(recorded.returncode, 0, recorded.stderr)

    def test_a_real_pass_report_closes_the_feature(self):
        self.bootstrap()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.record_pass()
        self.assertEqual(self.detect(), "phase=E action=done")

    def test_a_commit_after_the_pass_reopens_verification(self):
        # The gap dogfooding exposed: the report was PASS, but a task landed
        # after it and detect still said done (T34).
        #
        # The round number is 1, not 2: the commit closed the epoch that PASS
        # belonged to, and the tree it produced has been verified zero times.
        self.bootstrap()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.record_pass()
        self.assertEqual(self.detect(), "phase=E action=done")
        self.write("late.txt", "landed after the verification")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "docs: land something after the verification")
        self.assertEqual(self.detect(), "phase=V action=verify round=1")

    def test_the_driver_stops_on_done_instead_of_respawning(self):
        self.bootstrap()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.record_pass()
        proc = self.run_loop_sh()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[-1], "phase=E action=done")
        self.assert_no_executor_ran()

    def test_the_driver_never_prints_the_done_signature(self):
        # Scenario 15. `loop.sh` stops on `phase=E`; it does not conclude
        # anything. Only `finish_loop.py` can put that line in a transcript, so
        # a goal evaluator matching it is matching a deterministic decision.
        self.bootstrap()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")
        self.record_pass()
        proc = self.run_loop_sh()
        self.assertNotIn("__TLC_LOOP__", proc.stdout)
        self.assertNotIn("__TLC_LOOP__", proc.stderr)


    # ---- 6. the incident -------------------------------------------------
    #
    # Scenario 14: the real run, start to finish, ending in a signed E.
    #
    # What happened: a verifier passed commit `V` on the third of three allowed
    # rounds. A checkpoint then committed the report and the plan updates, and a
    # second one merged a base branch that had moved. Both gates passed. No
    # verifier had seen either tree, `verify.rounds` had reached its ceiling, and
    # the detector answered `verify_exhausted` with a detail claiming no PASS had
    # ever happened. The signature was printed anyway.
    #
    # Every test below is the same sequence with the machinery it was missing:
    # the report goes in as a seal, the merge goes in as a reopen, the reopened
    # epoch gets its own budget, and the signature comes from the finalizer.

    def bounded_run(self):
        """Bootstrap with `max_rounds = 3`, and land every task."""
        self.write_config("[verify]\nmax_rounds = 3\n")
        self.bootstrap()
        self.complete("T1", "T2", "T3", "T4", "T5", "T6")

    def record_round(self, verdict, report=PASS_REPORT):
        self.write(".specs/features/toy/validation.md", report)
        proc = self.run_script(
            "update_loop.py", "toy", "--root", self.root,
            "--verify-round", verdict, "--gaps", "0",
            "--report", ".specs/features/toy/validation.md",
            "--iteration-done", "--phase", "V", "--action", f"verify {verdict}",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def seal(self):
        proc = self.run_script("checkpoint.py", "toy", "--root", self.root, "--seal")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def spend_the_budget(self):
        """Two FAIL rounds, then the PASS on the third and last allowed one."""
        self.bounded_run()
        self.record_round("FAIL")
        self.record_round("FAIL")
        self.record_round("PASS")

    def base_branch_moves(self):
        """A commit lands on the base branch after the feature was verified."""
        _git(self.root, "checkout", "-q", "-b", "side", "HEAD~3")
        self.write("upstream.txt", "landed on main\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "feat(upstream): land something on main")
        _git(self.root, "checkout", "-q", "main")

    def test_the_pass_on_the_last_allowed_round_is_done(self):
        self.spend_the_budget()
        self.assertEqual(self.detect(), "phase=E action=done")

    def test_sealing_the_report_keeps_it_done(self):
        self.spend_the_budget()
        self.seal()
        self.assertEqual(self.detect(), "phase=E action=done")

    def test_the_merge_reopens_verification_instead_of_exhausting_it(self):
        self.spend_the_budget()
        self.seal()
        self.base_branch_moves()
        _git(self.root, "merge", "--no-commit", "--no-ff", "side", check=False)
        reopened = self.run_script(
            "checkpoint.py", "toy", "--root", self.root, "--reopen",
            "--message", "chore(toy): integrate the base branch",
        )
        self.assertEqual(reopened.returncode, 0, reopened.stderr)
        self.assertEqual(self.detect(), "phase=V action=verify round=1")

    def test_the_reopened_run_reaches_a_signed_done(self):
        self.spend_the_budget()
        self.seal()
        self.base_branch_moves()
        _git(self.root, "merge", "--no-commit", "--no-ff", "side", check=False)
        self.run_script(
            "checkpoint.py", "toy", "--root", self.root, "--reopen",
            "--message", "chore(toy): integrate the base branch",
        )
        self.record_round("PASS", SECOND_PASS_REPORT)
        self.seal()
        self.assertEqual(self.detect(), "phase=E action=done")

        finished = self.run_script("finish_loop.py", "toy", "--root", self.root)
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertEqual(
            finished.stdout.splitlines()[-1], "__TLC_LOOP__ feature=toy verify=PASS"
        )

    def test_the_signature_is_refused_before_the_second_verification(self):
        # The exact moment the real run signed. Every gate had passed and the
        # tree was two commits past the only verdict on record.
        self.spend_the_budget()
        self.seal()
        self.base_branch_moves()
        _git(self.root, "merge", "--no-commit", "--no-ff", "side", check=False)
        self.run_script(
            "checkpoint.py", "toy", "--root", self.root, "--reopen",
            "--message", "chore(toy): integrate the base branch",
        )
        finished = self.run_script("finish_loop.py", "toy", "--root", self.root)
        self.assertNotEqual(finished.returncode, 0)
        self.assertNotIn("__TLC_LOOP__", finished.stdout)

    def test_publishing_is_refused_while_the_base_is_ahead(self):
        # Scenario 11, in the run that needed it. `origin/main` carries a commit
        # HEAD does not, so a push would drag an unverified merge behind it.
        self.spend_the_budget()
        self.seal()
        self.base_branch_moves()
        _git(self.root, "update-ref", "refs/remotes/origin/main", "side")
        proc = self.run_script(
            "finish_loop.py", "toy", "--root", self.root, "--preflight", "origin/main"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("origin/main", proc.stderr)


if __name__ == "__main__":
    unittest.main()
