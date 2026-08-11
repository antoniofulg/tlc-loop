"""Unit tests for _gitio - commit-trailer task status (T5, LOOP-01).

Derived from T5's "Done when" criteria and:
  - LOOP-01 AC 2: completed tasks are read from git trailers via
    `git log --format="%(trailers:key=Task,valueonly)"` and that result is
    authoritative
  - spec.md edge case: "IF a commit is amended or rebased such that a `Task:`
    trailer is duplicated THEN the system SHALL treat the task as completed
    once and SHALL record the ambiguity"
  - LOOP-02 AC 1: the checkpoint commit carries `Task: <id>` and
    `Gate: <level> PASS`

Every test builds a real repository inside a TemporaryDirectory. Nothing here
touches the repository this project lives in.
"""

import os
import subprocess
import tempfile
import unittest

import _gitio


def _git(root, *args, check=True):
    proc = subprocess.run(
        ["git", "-C", root, *args], capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc


def _init(root):
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "loop@test.invalid")
    _git(root, "config", "user.name", "Loop Test")
    _git(root, "config", "commit.gpgsign", "false")


def _commit(root, filename, message, task=None, gate="quick"):
    with open(os.path.join(root, filename), "w", encoding="utf-8") as fh:
        fh.write(filename)
    _git(root, "add", filename)
    args = ["commit", "-q", "-m", message]
    if task:
        args += _gitio.trailer_args(task, gate)
    _git(root, *args)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


class IsGitRepo(unittest.TestCase):
    def test_true_inside_a_repository(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            self.assertTrue(_gitio.is_git_repo(root))

    def test_false_outside_a_repository(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(_gitio.is_git_repo(root))


class NoCommits(unittest.TestCase):
    def test_a_repository_with_no_commits_yields_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            self.assertEqual(_gitio.completed_tasks(root), ([], []))


class CommitsWithoutTrailers(unittest.TestCase):
    def test_they_contribute_nothing_and_produce_no_empty_entries(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "a.txt", "chore: one")
            _commit(root, "b.txt", "chore: two")
            ids, duplicates = _gitio.completed_tasks(root)
            self.assertEqual(ids, [])
            self.assertEqual(duplicates, [])
            self.assertNotIn("", ids)


class MixedCommits(unittest.TestCase):
    def test_only_trailered_commits_appear_in_first_seen_order(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "a.txt", "chore: untracked work")
            _commit(root, "b.txt", "feat: two", task="T2")
            _commit(root, "c.txt", "chore: more untracked work")
            _commit(root, "d.txt", "feat: one", task="T1")
            ids, duplicates = _gitio.completed_tasks(root)
            self.assertEqual(ids, ["T2", "T1"])
            self.assertEqual(duplicates, [])

    def test_no_blank_entry_survives_the_trailer_less_commits(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "a.txt", "chore: nothing")
            _commit(root, "b.txt", "feat: one", task="T1")
            ids, _ = _gitio.completed_tasks(root)
            self.assertEqual(ids, ["T1"])


class DuplicateTrailer(unittest.TestCase):
    def test_a_cherry_picked_commit_yields_one_entry_and_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "base.txt", "chore: base")
            t1 = _commit(root, "a.txt", "feat: one", task="T1")
            _git(root, "checkout", "-q", "-b", "side", "HEAD~1")
            _commit(root, "b.txt", "feat: two", task="T2")
            _git(root, "cherry-pick", t1)
            # merging main back brings the original commit alongside its copy,
            # so the same Task: T1 trailer now appears twice in one history
            _git(root, "merge", "--no-edit", "-q", "main")

            raw = _git(
                root, "log", "--format=%(trailers:key=Task,valueonly)"
            ).stdout.split()
            self.assertEqual(raw.count("T1"), 2, "fixture must really duplicate the trailer")

            ids, duplicates = _gitio.completed_tasks(root)
            self.assertEqual(ids.count("T1"), 1)
            self.assertEqual(sorted(ids), ["T1", "T2"])
            self.assertEqual(duplicates, ["T1"])

    def test_a_duplicate_is_reported_once_however_many_times_it_repeats(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "a.txt", "feat: one", task="T1")
            _commit(root, "b.txt", "feat: one again", task="T1")
            _commit(root, "c.txt", "feat: one once more", task="T1")
            ids, duplicates = _gitio.completed_tasks(root)
            self.assertEqual(ids, ["T1"])
            self.assertEqual(duplicates, ["T1"])


class NotARepository(unittest.TestCase):
    def test_completed_tasks_raises_giterror_naming_the_path(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(_gitio.GitError) as ctx:
                _gitio.completed_tasks(root)
            self.assertIn(os.path.abspath(root), str(ctx.exception))


class HeadCommit(unittest.TestCase):
    """The SHA a verification covers. Wrong here means a stale PASS is accepted."""

    def test_returns_the_current_head(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            sha = _commit(root, "a.txt", "chore: a")
            self.assertEqual(_gitio.head_commit(root), sha)

    def test_moves_with_a_new_commit(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            first = _commit(root, "a.txt", "chore: a")
            second = _commit(root, "b.txt", "chore: b")
            self.assertNotEqual(first, second)
            self.assertEqual(_gitio.head_commit(root), second)

    def test_a_repository_with_no_commits_has_no_head(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            self.assertIsNone(_gitio.head_commit(root))

    def test_outside_a_repository_there_is_no_head(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(_gitio.head_commit(root))


class DirtyPaths(unittest.TestCase):
    """What counts as a working-tree change when a seal or a finish asks.

    The parsing is the fiddly half - porcelain reports renames as two paths and
    quotes anything unusual - and the exclusion is the load-bearing half: the
    loop's own `loop.json` is machine state and must not be able to block a
    finish in a project that never added the `.gitignore` rule.
    """

    def test_a_clean_tree_reports_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "seed.txt", "chore: seed")
            self.assertEqual(_gitio.dirty_paths(root, "demo"), set())

    def test_an_untracked_file_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "seed.txt", "chore: seed")
            with open(os.path.join(root, "new.txt"), "w", encoding="utf-8") as fh:
                fh.write("new\n")
            self.assertEqual(_gitio.dirty_paths(root, "demo"), {"new.txt"})

    def test_a_staged_file_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "seed.txt", "chore: seed")
            with open(os.path.join(root, "new.txt"), "w", encoding="utf-8") as fh:
                fh.write("new\n")
            _git(root, "add", "-A")
            self.assertEqual(_gitio.dirty_paths(root, "demo"), {"new.txt"})

    def test_a_rename_reports_the_destination(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "before.txt", "chore: seed")
            _git(root, "mv", "before.txt", "after.txt")
            self.assertEqual(_gitio.dirty_paths(root, "demo"), {"after.txt"})

    def test_the_loops_own_state_file_is_excluded(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "seed.txt", "chore: seed")
            os.makedirs(os.path.join(root, ".specs", "features", "demo"))
            with open(
                os.path.join(root, ".specs/features/demo/loop.json"), "w", encoding="utf-8"
            ) as fh:
                fh.write("{}\n")
            self.assertEqual(_gitio.dirty_paths(root, "demo"), set())

    def test_another_features_state_file_is_not_excluded(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "seed.txt", "chore: seed")
            os.makedirs(os.path.join(root, ".specs", "features", "other"))
            with open(
                os.path.join(root, ".specs/features/other/loop.json"), "w", encoding="utf-8"
            ) as fh:
                fh.write("{}\n")
            self.assertEqual(
                _gitio.dirty_paths(root, "demo"), {".specs/features/other/loop.json"}
            )


class TrailerArgs(unittest.TestCase):
    def test_composes_task_and_gate_trailers(self):
        self.assertEqual(
            _gitio.trailer_args("T7", "build"),
            ["--trailer", "Task: T7", "--trailer", "Gate: build PASS"],
        )

    def test_the_composed_trailers_read_back_from_git(self):
        with tempfile.TemporaryDirectory() as root:
            _init(root)
            _commit(root, "a.txt", "feat: one", task="T3", gate="full")
            self.assertEqual(
                _git(root, "log", "-1", "--format=%(trailers:key=Task,valueonly)").stdout.strip(),
                "T3",
            )
            self.assertEqual(
                _git(root, "log", "-1", "--format=%(trailers:key=Gate,valueonly)").stdout.strip(),
                "full PASS",
            )


if __name__ == "__main__":
    unittest.main()
