"""Unit tests for checkpoint.py (T11, LOOP-02).

Derived from T11's "Done when" criteria and:
  - LOOP-02 AC 1: a passing gate produces one atomic commit carrying
    `Task: <id>` and `Gate: <level> PASS`
  - LOOP-02 AC 2: no commit is created when the gate has not passed
  - LOOP-02 AC 3: the message is validated with `check_commit.py` and a
    non-zero exit aborts the commit
  - LOOP-02 AC 4: at most one commit per task, never batched
  - LOOP-02 AC 6: a task producing no file changes records completion without
    fabricating a source diff - as an empty commit carrying the trailers (T37)

Each test builds a throwaway skill layout - this skill plus a sibling
`tlc-spec-driven` - and a separate tmpdir git repo. The sibling's
`check_commit.py` is a stub honouring its documented contract (exit 1 on a
header that is not Conventional Commits); the real validator is mutation
tested separately in T25. The stub records the message it was handed, which is
what proves checkpoint actually consulted it rather than validating inline.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

from test_unit_detect_phase import VALIDATE_STATE_STUB  # noqa: E402

CHECK_COMMIT_STUB = '''#!/usr/bin/env python3
import os, re, sys
msg = sys.argv[sys.argv.index("--message") + 1] if "--message" in sys.argv else ""
marker = os.environ.get("CHECK_COMMIT_MARKER")
if marker:
    with open(marker, "w", encoding="utf-8") as fh:
        fh.write(msg)
lines = msg.splitlines()
header = lines[0] if lines else ""
ok = re.match(r"^(feat|fix|docs|test|chore|refactor|perf|build|ci|style)"
              r"(\\([^)]+\\))?!?: [a-z].*$", header)
sys.exit(0 if ok else 1)
'''

GOOD_MESSAGE = "feat(loop): add the thing"
BAD_MESSAGE = "Added The Thing."

# The parent skill's own convention puts the trailers in the message body, so
# this is what a conforming caller actually hands over.
TRAILERED_MESSAGE = "feat(loop): add the thing\n\nTask: T7\nGate: quick PASS"


def _git(root, *args, check=True):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc


class CheckpointCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = self.tmp.name

        self.skill_scripts = os.path.join(base, "skills", "tlc-loop", "scripts")
        os.makedirs(self.skill_scripts)
        for name in os.listdir(SCRIPTS):
            if name.endswith(".py") and not name.startswith("test_"):
                shutil.copyfile(
                    os.path.join(SCRIPTS, name), os.path.join(self.skill_scripts, name)
                )

        self.tlc_scripts = os.path.join(base, "skills", "tlc-spec-driven", "scripts")
        os.makedirs(self.tlc_scripts)
        with open(os.path.join(self.tlc_scripts, "check_commit.py"), "w", encoding="utf-8") as fh:
            fh.write(CHECK_COMMIT_STUB)
        # `checkpoint.py` asks `detect_phase.py` what phase the run is in, and
        # the detector reaches the sibling's completion gate once nothing is
        # pending. Both stubs are here for the same reason: the sibling skill is
        # a hard dependency of this one, and a fixture missing it tests a
        # situation no install has.
        with open(os.path.join(self.tlc_scripts, "validate_state.py"), "w", encoding="utf-8") as fh:
            fh.write(VALIDATE_STATE_STUB)

        self.marker = os.path.join(base, "check_commit_called.txt")
        self.root = os.path.join(base, "project")
        os.makedirs(os.path.join(self.root, ".specs", "features", "demo"))
        with open(os.path.join(self.root, ".specs", "features", "demo", "tasks.md"), "w") as fh:
            fh.write("# demo Tasks\n")

        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "loop@test.invalid")
        _git(self.root, "config", "user.name", "Loop Test")
        _git(self.root, "config", "commit.gpgsign", "false")
        self.write("seed.txt", "seed")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "chore: seed")

    # ---- fixture helpers -------------------------------------------------

    def write(self, name, text):
        path = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def run_checkpoint(self, *args):
        env = dict(os.environ, CHECK_COMMIT_MARKER=self.marker)
        return subprocess.run(
            [
                sys.executable,
                os.path.join(self.skill_scripts, "checkpoint.py"),
                "demo",
                "--root",
                self.root,
                *args,
            ],
            capture_output=True,
            text=True,
            env=env,
        )

    def checkpoint(self, task="T7", gate="quick", result="PASS", message=GOOD_MESSAGE, *extra):
        args = ["--task", task, "--gate", gate, "--message", message, *extra]
        if result is not None:
            args += ["--gate-result", result]
        return self.run_checkpoint(*args)

    def commit_count(self):
        return int(_git(self.root, "rev-list", "--count", "HEAD").stdout.strip())

    def trailer(self, key):
        return _git(
            self.root, "log", "-1", f"--format=%(trailers:key={key},valueonly)"
        ).stdout.strip()

    def staged(self):
        return _git(self.root, "diff", "--cached", "--name-only").stdout.split()


class GateMustPass(CheckpointCase):
    """LOOP-02 AC 2: no passing gate asserted, no commit."""

    def test_an_omitted_gate_result_refuses_and_commits_nothing(self):
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint(result=None)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.commit_count(), before)

    def test_a_failing_gate_result_refuses_and_commits_nothing(self):
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint(result="FAIL")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.commit_count(), before)

    def test_a_gate_result_that_is_not_exactly_pass_refuses(self):
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint(result="pass")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.commit_count(), before)

    def test_the_refusal_leaves_the_work_uncommitted_rather_than_discarding_it(self):
        self.write("work.txt", "changed")
        self.checkpoint(result="FAIL")
        self.assertIn("work.txt", _git(self.root, "status", "--porcelain").stdout)


class MessageValidatedBeforeStaging(CheckpointCase):
    """LOOP-02 AC 3: check_commit.py gates the commit, before anything is staged."""

    def test_an_invalid_message_refuses(self):
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint(message=BAD_MESSAGE)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.commit_count(), before)

    def test_an_invalid_message_leaves_nothing_staged(self):
        self.write("work.txt", "changed")
        self.checkpoint(message=BAD_MESSAGE)
        self.assertEqual(self.staged(), [])

    def test_the_sibling_validator_is_the_one_consulted(self):
        self.write("work.txt", "changed")
        self.checkpoint()
        self.assertTrue(os.path.isfile(self.marker), "check_commit.py was never invoked")
        with open(self.marker, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), GOOD_MESSAGE)

    def test_the_validator_runs_even_when_the_message_is_rejected(self):
        self.write("work.txt", "changed")
        self.checkpoint(message=BAD_MESSAGE)
        with open(self.marker, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), BAD_MESSAGE)


class SuccessfulCheckpoint(CheckpointCase):
    """LOOP-02 AC 1 and AC 4."""

    def test_it_exits_zero_and_creates_exactly_one_commit(self):
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.commit_count(), before + 1)

    def test_the_task_trailer_reads_back_through_the_documented_format(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7")
        self.assertEqual(self.trailer("Task"), "T7")

    def test_the_gate_trailer_records_the_level_and_pass(self):
        self.write("work.txt", "changed")
        self.checkpoint(gate="build")
        self.assertEqual(self.trailer("Gate"), "build PASS")

    def test_the_short_sha_is_printed(self):
        self.write("work.txt", "changed")
        proc = self.checkpoint()
        head = _git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        self.assertIn(head, proc.stdout)

    def test_the_commit_carries_the_message_it_was_given(self):
        self.write("work.txt", "changed")
        self.checkpoint()
        subject = _git(self.root, "log", "-1", "--format=%s").stdout.strip()
        self.assertEqual(subject, "feat(loop): add the thing")

    def test_the_working_tree_is_clean_afterwards(self):
        self.write("work.txt", "changed")
        self.checkpoint()
        self.assertEqual(_git(self.root, "status", "--porcelain").stdout.strip(), "")


class MessageAlreadyCarriesTrailers(CheckpointCase):
    """A conforming caller writes the trailers itself; they must not double up.

    `_gitio.completed_tasks` reads a repeated `Task:` as the rebase ambiguity
    described in spec.md's edge cases. Appending a trailer the message already
    has would make every ordinary checkpoint look ambiguous.
    """

    def test_the_task_trailer_appears_exactly_once(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7", gate="quick", message=TRAILERED_MESSAGE)
        self.assertEqual(self.trailer("Task"), "T7")

    def test_the_gate_trailer_appears_exactly_once(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7", gate="quick", message=TRAILERED_MESSAGE)
        self.assertEqual(self.trailer("Gate"), "quick PASS")

    def test_the_commit_is_not_reported_as_a_duplicate_by_gitio(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7", gate="quick", message=TRAILERED_MESSAGE)
        sys.path.insert(0, SCRIPTS)
        import _gitio

        ids, duplicates = _gitio.completed_tasks(self.root)
        self.assertEqual(ids, ["T7"])
        self.assertEqual(duplicates, [])

    def test_a_task_trailer_contradicting_the_flag_is_refused(self):
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint(task="T9", gate="quick", message=TRAILERED_MESSAGE)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.commit_count(), before)

    def test_a_gate_trailer_contradicting_the_flag_is_refused(self):
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint(task="T7", gate="build", message=TRAILERED_MESSAGE)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.commit_count(), before)


class NoDiffPath(CheckpointCase):
    """T37 / LOOP-02 AC 6: a task with no diff is recorded as an empty commit.

    AC 6 forbids fabricating a source diff, not committing. An empty commit
    fabricates nothing and carries the trailers, which is what makes the
    completion durable in git instead of only in `loop.json`.
    """

    def test_it_exits_zero(self):
        self.assertEqual(self.checkpoint().returncode, 0)

    def test_it_creates_a_commit(self):
        before = self.commit_count()
        self.checkpoint()
        self.assertEqual(self.commit_count(), before + 1)

    def test_that_commit_carries_the_task_trailer(self):
        self.checkpoint(task="T7")
        self.assertEqual(self.trailer("Task"), "T7")

    def test_that_commit_carries_the_gate_trailer(self):
        self.checkpoint(task="T7", gate="quick")
        self.assertEqual(self.trailer("Gate"), "quick PASS")

    def test_that_commit_fabricates_no_source_diff(self):
        self.checkpoint()
        changed = _git(
            self.root, "show", "--name-only", "--format=", "HEAD"
        ).stdout.split()
        self.assertEqual(changed, [])

    def test_the_line_reports_the_commit_as_empty(self):
        proc = self.checkpoint(task="T7", gate="quick")
        sha = _git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        self.assertEqual(proc.stdout.strip(), f"{sha} T7 gate=quick PASS empty")

    def test_a_task_that_changed_something_is_not_reported_as_empty(self):
        self.write("work.txt", "changed")
        proc = self.checkpoint(task="T7", gate="quick")
        self.assertNotIn("empty", proc.stdout)

    def test_completed_tasks_reads_the_no_diff_task_back(self):
        # The point of the empty commit: `_gitio` sees it like any other task,
        # so completion no longer depends on `loop.json` surviving.
        self.checkpoint(task="T7")
        sys.path.insert(0, SCRIPTS)
        import _gitio

        ids, duplicates = _gitio.completed_tasks(self.root)
        self.assertEqual(ids, ["T7"])
        self.assertEqual(duplicates, [])


class SelectiveStaging(CheckpointCase):
    """Design: stage the task's files plus the feature's traceability updates."""

    def test_named_paths_are_committed(self):
        self.write("mine.txt", "task work")
        self.checkpoint("T7", "quick", "PASS", GOOD_MESSAGE, "--path", "mine.txt")
        files = _git(self.root, "show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertIn("mine.txt", files)

    def test_unnamed_paths_are_left_uncommitted(self):
        self.write("mine.txt", "task work")
        self.write("theirs.txt", "unrelated")
        self.checkpoint("T7", "quick", "PASS", GOOD_MESSAGE, "--path", "mine.txt")
        self.assertIn("theirs.txt", _git(self.root, "status", "--porcelain").stdout)

    def test_the_feature_tasks_md_rides_along_with_named_paths(self):
        self.write("mine.txt", "task work")
        self.write(".specs/features/demo/tasks.md", "# demo Tasks\n\n### T7 done\n")
        self.checkpoint("T7", "quick", "PASS", GOOD_MESSAGE, "--path", "mine.txt")
        files = _git(self.root, "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn(".specs/features/demo/tasks.md", files)


class LoopStateStaysOutOfCommits(CheckpointCase):
    """T30 / LOOP-02 AC 1: a task commit carries the task's work, not the cache.

    With no `--path`, `checkpoint.py` stages everything. `loop.json` is
    machine-owned state that git can already reconstruct, so sweeping it into a
    task's atomic commit adds a counter bump to a diff that is supposed to be
    one task's implementation and tests.

    The fixture installs the shipped `.gitignore` verbatim rather than a
    hand-written pattern, so dropping the rule from the real file fails here.
    """

    GITIGNORE = os.path.join(os.path.dirname(SCRIPTS), ".gitignore")

    def setUp(self):
        super().setUp()
        shutil.copyfile(self.GITIGNORE, os.path.join(self.root, ".gitignore"))
        # A real state file, because `checkpoint.py` asks `detect_phase.py` what
        # phase the run is in and an unreadable one is `phase=H` - a refusal,
        # not a fixture. What is under test here is where the file ends up, not
        # what is in it.
        sys.path.insert(0, SCRIPTS)
        import _state_io

        self.write(
            ".specs/features/demo/loop.json",
            json.dumps(_state_io.new_state("demo", "ship demo", "claude"), indent=2) + "\n",
        )

    def committed_files(self):
        return _git(
            self.root, "show", "--name-only", "--format=", "HEAD"
        ).stdout.split()

    def test_a_path_less_checkpoint_leaves_loop_json_out_of_the_commit(self):
        self.write("work.txt", "task work")
        self.checkpoint()
        self.assertNotIn(".specs/features/demo/loop.json", self.committed_files())

    def test_the_task_work_is_still_committed(self):
        self.write("work.txt", "task work")
        self.checkpoint()
        self.assertIn("work.txt", self.committed_files())

    def test_the_state_file_survives_on_disk(self):
        # Ignored, not deleted: the run still needs its counters.
        self.write("work.txt", "task work")
        self.checkpoint()
        self.assertTrue(
            os.path.isfile(os.path.join(self.root, ".specs/features/demo/loop.json"))
        )

    def test_it_is_ignored_under_any_feature_directory(self):
        self.write(".specs/features/other-feature/loop.json", "{}\n")
        ignored = _git(
            self.root,
            "check-ignore",
            ".specs/features/demo/loop.json",
            ".specs/features/other-feature/loop.json",
        ).stdout.split()
        self.assertEqual(
            ignored,
            [".specs/features/demo/loop.json", ".specs/features/other-feature/loop.json"],
        )


class NoTrackedFileBecomesIgnored(unittest.TestCase):
    """T30: the new rule must not shadow a file this repo already tracks."""

    def test_no_tracked_file_matches_an_ignore_rule(self):
        repo = os.path.dirname(SCRIPTS)
        proc = subprocess.run(
            ["git", "-C", repo, "rev-parse", "--git-dir"], capture_output=True, text=True
        )
        if proc.returncode != 0:
            self.skipTest(f"{repo} is not a git repository")
        listed = subprocess.run(
            ["git", "-C", repo, "ls-files", "-i", "-c", "--exclude-standard"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(listed.stdout.strip(), "")


class NeverBypassesHooks(unittest.TestCase):
    """The implementation must not carry git's hook-bypass flag at all."""

    def test_the_bypass_flag_appears_nowhere_in_the_source(self):
        with open(os.path.join(SCRIPTS, "checkpoint.py"), encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("--no-verify", source)


#: A one-task plan, complete enough for `detect_phase.py` to route and answer.
PHASED_TASKS_MD = """# demo Tasks

## Execution Plan

### Phase 1: Foundation

```
T1
```

## Task Breakdown

### T1: One
**Tests**: unit
**Gate**: quick
"""

PASS_REPORT = "## Validation: demo - PASS\n\nEvidence: scripts/a.py:12\n"


class PhaseAwareCase(CheckpointCase):
    """A checkpoint fixture that also carries loop state and a routable plan.

    `checkpoint.py` asks `detect_phase.py` what phase the run is in before it
    writes anything, so these tests need the same inputs the detector needs: a
    parseable `tasks.md`, a `loop.json`, and the sibling's `validate_state.py`.
    The base fixture deliberately has none of them - its runs answer `phase=0`,
    which is the one phase where every ordinary checkpoint is allowed.
    """

    def setUp(self):
        super().setUp()
        self.feature_dir = os.path.join(self.root, ".specs", "features", "demo")
        self.write(".specs/features/demo/tasks.md", PHASED_TASKS_MD)
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "chore: add the plan")

    # ---- fixture helpers -------------------------------------------------

    def head(self):
        return _git(self.root, "rev-parse", "HEAD").stdout.strip()

    def write_state(self, **overrides):
        sys.path.insert(0, SCRIPTS)
        import _state_io

        state = _state_io.new_state("demo", "ship demo", "claude")
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(state.get(key), dict):
                state[key].update(value)
            else:
                state[key] = value
        with open(os.path.join(self.feature_dir, "loop.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        return state

    def write_report(self, text=PASS_REPORT):
        self.write(".specs/features/demo/validation.md", text)

    def detect(self):
        proc = subprocess.run(
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
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def reach_pass(self):
        """Land the plan's one task, then record a PASS stamped on that HEAD.

        This is the state the incident started from: a real verdict, covering
        the tree exactly as the verifier saw it, with the report still loose in
        the working tree.
        """
        self.write("src/one.py", "# T1\n")
        self.checkpoint(task="T1", gate="quick", message="feat(demo): add one")
        self.write_report()
        self.write_state(
            verify={
                "rounds": 3,
                "epoch_rounds": 3,
                "last_verdict": "PASS",
                "gaps_open": 0,
                "verified_at": self.head(),
            }
        )
        return self.head()

    def seal(self, *extra):
        return self.run_checkpoint("--seal", *extra)


class TheSeal(PhaseAwareCase):
    """Scenarios 2 and 3: the one commit allowed to follow a PASS.

    A verifier reads the tree at commit `V` and writes `validation.md`. Nothing
    can commit that report without moving HEAD past `V`, and a moved HEAD is by
    construction unverified - which is the circularity that left the real run
    with a genuine PASS it could never sign for.

    The seal breaks it by being narrow enough to reason about: exactly one file,
    exactly one parent, trailers naming the commit it certifies. The detector
    re-derives all three rather than trusting the trailers.
    """

    def test_it_commits_and_stays_at_phase_e(self):
        self.reach_pass()
        proc = self.seal()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.detect(), "phase=E action=done")

    def test_the_seal_carries_only_the_validation_report(self):
        self.reach_pass()
        self.seal()
        changed = _git(
            self.root, "show", "--name-only", "--format=", "HEAD"
        ).stdout.split()
        self.assertEqual(changed, [".specs/features/demo/validation.md"])

    def test_its_parent_is_the_verified_commit(self):
        verified_at = self.reach_pass()
        self.seal()
        parent = _git(self.root, "rev-parse", "HEAD^").stdout.strip()
        self.assertEqual(parent, verified_at)

    def test_it_names_the_commit_it_certifies(self):
        verified_at = self.reach_pass()
        self.seal()
        self.assertEqual(self.trailer("Verification-Of"), verified_at)

    def test_it_records_the_verdict(self):
        self.reach_pass()
        self.seal()
        self.assertEqual(self.trailer("Verification-Result"), "PASS")

    def test_it_carries_no_task_trailer(self):
        # A `Task:` trailer means "a gate passed for a planned task". Inventing
        # one to smuggle the report past the checkpoint is what produced the
        # incident's F14 commit.
        self.reach_pass()
        self.seal()
        self.assertEqual(self.trailer("Task"), "")

    def test_a_second_file_in_the_tree_refuses(self):
        self.reach_pass()
        self.write("src/extra.py", "# snuck in\n")
        before = self.commit_count()
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(self.commit_count(), before)

    def test_a_staged_second_file_refuses_too(self):
        self.reach_pass()
        self.write("src/extra.py", "# snuck in\n")
        _git(self.root, "add", "-A")
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)

    def test_a_modified_tasks_md_refuses(self):
        # Plan and design updates belong before the final verification, not in
        # the exception carved out for the evidence.
        self.reach_pass()
        self.write(".specs/features/demo/tasks.md", PHASED_TASKS_MD + "\n<!-- late -->\n")
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("tasks.md", proc.stderr)

    def test_a_fail_report_refuses(self):
        self.reach_pass()
        self.write_report("## Validation: demo - FAIL\n\nEvidence: scripts/a.py:12\n")
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)

    def test_an_empty_report_refuses(self):
        self.reach_pass()
        self.write_report("")
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)

    def test_a_report_with_no_evidence_refuses(self):
        self.reach_pass()
        self.write_report("## Validation: demo - PASS\n\nLooks good to me.\n")
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)

    def test_a_verdict_that_does_not_cover_head_refuses(self):
        self.reach_pass()
        _git(self.root, "commit", "-q", "--allow-empty", "-m", "chore: move head along")
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)

    def test_nothing_to_seal_refuses(self):
        self.reach_pass()
        self.seal()
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)

    def test_a_second_seal_on_top_of_a_seal_is_not_coverage(self):
        # Only a direct child of `verified_at` counts. A chain would let any
        # number of commits ride behind one verdict.
        self.reach_pass()
        self.seal()
        self.write_report(PASS_REPORT + "\nAppended after the seal.\n")
        proc = self.seal()
        self.assertEqual(proc.returncode, 2)


class CommitsAfterDoneAreRefused(PhaseAwareCase):
    """Scenario 9: `checkpoint.py` will not extend a finished run.

    The incident's F14 and F15 commits went in after the verifier had passed,
    each one carrying a synthetic `Task:` id that no plan declares. Both were
    accepted because nothing asked what phase the run was in.
    """

    def test_an_ordinary_checkpoint_in_phase_e_refuses(self):
        self.reach_pass()
        self.seal()
        self.write("src/late.py", "# late\n")
        before = self.commit_count()
        proc = self.checkpoint(task="T2", gate="quick", message="feat(demo): add late")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(self.commit_count(), before)

    def test_the_refusal_names_the_phase(self):
        self.reach_pass()
        self.seal()
        proc = self.checkpoint(task="T2", gate="quick", message="feat(demo): add late")
        self.assertIn("phase=E", proc.stderr)

    def test_an_ordinary_checkpoint_in_phase_h_refuses(self):
        self.reach_pass()
        self.write_state(
            halt={"reason": "blast_radius", "detail": "push required"}, status="halted"
        )
        before = self.commit_count()
        proc = self.checkpoint(task="T2", gate="quick", message="feat(demo): add late")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(self.commit_count(), before)

    def test_the_refusal_leaves_the_work_in_the_tree(self):
        self.reach_pass()
        self.seal()
        self.write("src/late.py", "# late\n")
        self.checkpoint(task="T2", gate="quick", message="feat(demo): add late")
        self.assertIn("src/late.py", _git(self.root, "status", "--porcelain").stdout)

    def test_a_batch_phase_still_commits(self):
        # The guard is about E and H. Everything else is ordinary work.
        self.write_state()
        self.write("src/one.py", "# T1\n")
        proc = self.checkpoint(task="T1", gate="quick", message="feat(demo): add one")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_an_unreadable_situation_refuses_rather_than_guessing(self):
        self.write(".specs/features/demo/loop.json", "{ not json")
        proc = self.checkpoint(task="T1", gate="quick", message="feat(demo): add one")
        self.assertEqual(proc.returncode, 2)


class LateBaseIntegration(PhaseAwareCase):
    """Scenario 10: the one way to commit after a PASS and stay honest.

    A base branch moving under a finished feature is not a documentation edit
    and cannot ride the seal's exception. `--reopen` is the authorized writer's
    route for it: the commit lands, the previous conclusion stops covering HEAD,
    and the next detect asks for a verifier that has seen the merged tree.
    """

    def side_branch(self):
        """A commit on a divergent branch, standing in for `origin/main`."""
        base = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        _git(self.root, "checkout", "-q", "-b", "side", f"{base}~1")
        self.write("upstream.txt", "landed upstream\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "feat(upstream): land something")
        _git(self.root, "checkout", "-q", "main")

    def reopen(self, message="chore(demo): integrate the base branch"):
        return self.run_checkpoint("--reopen", "--message", message)

    def test_it_commits_where_an_ordinary_checkpoint_is_refused(self):
        self.reach_pass()
        self.seal()
        self.write("integrated.txt", "merged\n")
        before = self.commit_count()
        proc = self.reopen()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.commit_count(), before + 1)

    def test_it_names_the_verdict_it_invalidates(self):
        verified_at = self.reach_pass()
        self.seal()
        self.write("integrated.txt", "merged\n")
        self.reopen()
        self.assertEqual(self.trailer("Reopens-Verification"), verified_at)

    def test_it_carries_no_task_trailer(self):
        self.reach_pass()
        self.seal()
        self.write("integrated.txt", "merged\n")
        self.reopen()
        self.assertEqual(self.trailer("Task"), "")

    def test_the_next_detect_asks_for_a_fresh_verification(self):
        self.reach_pass()
        self.seal()
        self.write("integrated.txt", "merged\n")
        self.reopen()
        self.assertEqual(self.detect(), "phase=V action=verify round=1")

    def test_a_real_merge_keeps_both_parents(self):
        self.side_branch()
        self.reach_pass()
        self.seal()
        _git(self.root, "merge", "--no-commit", "--no-ff", "side", check=False)
        proc = self.reopen()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        parents = _git(self.root, "rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
        self.assertEqual(len(parents), 3, parents)

    def test_it_cannot_stand_in_for_the_seal(self):
        # The seal's exception is the report and nothing else. A reopen that
        # happened to touch only the report must still reopen, not certify.
        self.reach_pass()
        proc = self.reopen("docs(demo): record the validation report")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.trailer("Verification-Result"), "")
        self.assertEqual(self.detect(), "phase=V action=verify round=1")


class GateMatchesTheDeclaration(CheckpointCase):
    """Scenario 12: the trailer records the gate the task asked for.

    T7 in the real run declared `feature E2E` and its trailer read
    `Gate: full PASS`, because the flag accepted only three fixed levels and the
    caller picked the nearest one. A recorded gate that is not the declared gate
    is a false traceability record: it says a different command passed.
    """

    def declare(self, gate):
        self.write(
            ".specs/features/demo/tasks.md",
            f"# demo Tasks\n\n## Task Breakdown\n\n### T7: Seven\n"
            f"**Tests**: unit\n**Gate**: {gate}\n",
        )

    def test_a_declared_free_form_gate_reaches_the_trailer(self):
        self.declare("feature E2E")
        self.write("work.txt", "changed")
        proc = self.checkpoint(task="T7", gate="feature E2E")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.trailer("Gate"), "feature E2E PASS")

    def test_a_gate_that_contradicts_the_declaration_refuses(self):
        self.declare("feature E2E")
        self.write("work.txt", "changed")
        before = self.commit_count()
        proc = self.checkpoint(task="T7", gate="full")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(self.commit_count(), before)

    def test_the_refusal_names_both_sides(self):
        self.declare("feature E2E")
        proc = self.checkpoint(task="T7", gate="full")
        self.assertIn("feature E2E", proc.stderr)
        self.assertIn("full", proc.stderr)

    def test_the_comparison_ignores_case_and_spacing(self):
        self.declare("Feature   E2E")
        self.write("work.txt", "changed")
        proc = self.checkpoint(task="T7", gate="feature e2e")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_an_undeclared_task_still_takes_the_known_levels(self):
        self.write("work.txt", "changed")
        proc = self.checkpoint(task="T7", gate="quick")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_an_undeclared_task_refuses_an_invented_level(self):
        self.write("work.txt", "changed")
        proc = self.checkpoint(task="T7", gate="vibes")
        self.assertEqual(proc.returncode, 2)


class TheTaskIsTickedInTheSameCommit(CheckpointCase):
    """The plan is marked when the gate passes, not after the verifier runs.

    A tick applied later is a second commit against a verified tree. Applying it
    here keeps `tasks.md` and the trailers agreeing, which is the disagreement
    `reconciled=` exists to report.
    """

    def setUp(self):
        super().setUp()
        self.write(
            ".specs/features/demo/tasks.md",
            "# demo Tasks\n\n## Task Breakdown\n\n### T7: Seven\n"
            "**Tests**: unit\n**Gate**: quick\n",
        )
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "chore: add the plan")

    def plan(self):
        with open(
            os.path.join(self.root, ".specs/features/demo/tasks.md"), encoding="utf-8"
        ) as fh:
            return fh.read()

    def test_the_header_is_ticked(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7", gate="quick")
        self.assertIn("### T7: Seven ✅", self.plan())

    def test_the_tick_rides_the_task_commit(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7", gate="quick")
        files = _git(self.root, "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn(".specs/features/demo/tasks.md", files)

    def test_the_tree_is_clean_afterwards(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7", gate="quick")
        self.assertEqual(_git(self.root, "status", "--porcelain").stdout.strip(), "")

    def test_ticking_twice_does_not_double_the_mark(self):
        self.write("work.txt", "changed")
        self.checkpoint(task="T7", gate="quick")
        self.write("more.txt", "changed")
        self.checkpoint(task="T7", gate="quick")
        self.assertEqual(self.plan().count("✅"), 1)

    def test_a_task_the_plan_does_not_declare_changes_nothing(self):
        before = self.plan()
        self.write("work.txt", "changed")
        self.checkpoint(task="T9", gate="quick")
        self.assertEqual(self.plan(), before)


class NotARepository(CheckpointCase):
    def test_it_refuses_outside_a_git_repository(self):
        outside = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(os.path.join(outside, ".specs", "features", "demo"))
        proc = subprocess.run(
            [
                sys.executable,
                os.path.join(self.skill_scripts, "checkpoint.py"),
                "demo",
                "--root", outside,
                "--task", "T7",
                "--gate", "quick",
                "--gate-result", "PASS",
                "--message", GOOD_MESSAGE,
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
