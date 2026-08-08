"""Unit tests for checkpoint.py (T11, LOOP-02).

Derived from T11's "Done when" criteria and:
  - LOOP-02 AC 1: a passing gate produces one atomic commit carrying
    `Task: <id>` and `Gate: <level> PASS`
  - LOOP-02 AC 2: no commit is created when the gate has not passed
  - LOOP-02 AC 3: the message is validated with `check_commit.py` and a
    non-zero exit aborts the commit
  - LOOP-02 AC 4: at most one commit per task, never batched
  - LOOP-02 AC 6: a task producing no file changes records completion without
    fabricating a source diff

Each test builds a throwaway skill layout - this skill plus a sibling
`tlc-spec-driven` - and a separate tmpdir git repo. The sibling's
`check_commit.py` is a stub honouring its documented contract (exit 1 on a
header that is not Conventional Commits); the real validator is mutation
tested separately in T25. The stub records the message it was handed, which is
what proves checkpoint actually consulted it rather than validating inline.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))

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

        tlc_scripts = os.path.join(base, "skills", "tlc-spec-driven", "scripts")
        os.makedirs(tlc_scripts)
        with open(os.path.join(tlc_scripts, "check_commit.py"), "w", encoding="utf-8") as fh:
            fh.write(CHECK_COMMIT_STUB)

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


class NoChangesPath(CheckpointCase):
    """LOOP-02 AC 6: a task with no diff completes without an empty commit."""

    def test_it_prints_the_skip_line(self):
        proc = self.checkpoint()
        self.assertIn("SKIP: no changes", proc.stdout)

    def test_it_exits_zero(self):
        self.assertEqual(self.checkpoint().returncode, 0)

    def test_it_creates_no_commit(self):
        before = self.commit_count()
        self.checkpoint()
        self.assertEqual(self.commit_count(), before)


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
        self.write(".specs/features/demo/loop.json", '{"feature": "demo"}\n')

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
