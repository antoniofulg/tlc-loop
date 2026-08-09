"""Unit tests for _batching - phase packing (T7, LOOP-01).

Derived from T7's "Done when" criteria and the batching algorithm in
`tlc-spec-driven/references/sub-agents.md`:

  1. count total tasks
  2. T <= ~8 -> a single batch
  3. walk phases in order, accumulating whole phases into the current batch
  4. never split a phase across batches
  5. fold a lone tail batch of 1-2 tasks into the previous batch

plus the coarse-phase caveat: a phase over ~1.5x the budget is a Tasks-authoring
smell that must be surfaced, never resolved by splitting.
"""

import unittest

import _batching


def _tasks(sizes):
    """Build task dicts for phases of the given sizes: [3, 2] -> P1 x3, P2 x2."""
    out, counter = [], 0
    for phase, size in enumerate(sizes, start=1):
        for _ in range(size):
            counter += 1
            out.append({"id": f"T{counter}", "phase": phase})
    return out


def _routed_tasks(sizes, stages):
    tasks = _tasks(sizes)
    for task in tasks:
        task["effective_stage"] = stages[task["phase"] - 1]
    return tasks


class PhaseIntegrity(unittest.TestCase):
    """Rule 4 - the cut only ever lands on a phase boundary."""

    def _assert_whole_phases(self, sizes, budget=7):
        tasks = _tasks(sizes)
        batches, _ = _batching.pack(tasks, budget)
        by_phase = {}
        for task in tasks:
            by_phase.setdefault(task["phase"], []).append(task["id"])

        seen_phases = []
        for batch in batches:
            seen_phases += batch["phases"]
            # every task of every phase in this batch, and nothing else
            expected = [tid for phase in batch["phases"] for tid in by_phase[phase]]
            self.assertEqual(batch["tasks"], expected)
        # each phase lands in exactly one batch, and phase order is preserved
        self.assertEqual(seen_phases, sorted(by_phase))
        return batches

    def test_no_phase_is_split_across_batches(self):
        for sizes in ([3, 3, 3, 3, 4, 4], [8, 2, 2, 8], [5, 5, 5, 5], [11, 3], [7, 2]):
            with self.subTest(sizes=sizes):
                self._assert_whole_phases(sizes)

    def test_batches_are_consecutive_phases(self):
        batches, _ = _batching.pack(_tasks([3, 3, 3, 3, 4, 4]), 7)
        for batch in batches:
            phases = batch["phases"]
            self.assertEqual(phases, list(range(phases[0], phases[-1] + 1)))


class WorkedExamples(unittest.TestCase):
    """The three examples spelled out in sub-agents.md."""

    def test_3_3_3_3_4_4_yields_three_batches(self):
        batches, _ = _batching.pack(_tasks([3, 3, 3, 3, 4, 4]), 7)
        self.assertEqual(len(batches), 3)

    def test_8_2_2_8_yields_three_batches(self):
        batches, _ = _batching.pack(_tasks([8, 2, 2, 8]), 7)
        self.assertEqual(len(batches), 3)
        self.assertEqual([len(b["tasks"]) for b in batches], [8, 4, 8])

    def test_5_5_5_5_yields_two_batches(self):
        batches, _ = _batching.pack(_tasks([5, 5, 5, 5]), 7)
        self.assertEqual(len(batches), 2)
        self.assertEqual([len(b["tasks"]) for b in batches], [10, 10])

    def test_every_example_keeps_all_twenty_tasks(self):
        for sizes in ([3, 3, 3, 3, 4, 4], [8, 2, 2, 8], [5, 5, 5, 5]):
            with self.subTest(sizes=sizes):
                tasks = _tasks(sizes)
                batches, _ = _batching.pack(tasks, 7)
                packed = [tid for batch in batches for tid in batch["tasks"]]
                self.assertEqual(packed, [t["id"] for t in tasks])


class SmallFeature(unittest.TestCase):
    """Rule 2 - a feature that fits the budget is one batch."""

    def test_eight_tasks_fit_a_single_batch(self):
        batches, _ = _batching.pack(_tasks([4, 4]), 7)
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]["tasks"]), 8)

    def test_no_tasks_yields_no_batches(self):
        self.assertEqual(_batching.pack([], 7), ([], []))


class TailFolding(unittest.TestCase):
    """Rule 5 - a lone tail of one or two tasks joins the previous batch."""

    def test_a_two_task_tail_is_folded_into_the_previous_batch(self):
        batches, _ = _batching.pack(_tasks([7, 2]), 7)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["phases"], [1, 2])
        self.assertEqual(len(batches[0]["tasks"]), 9)

    def test_a_one_task_tail_is_folded_into_the_previous_batch(self):
        batches, _ = _batching.pack(_tasks([8, 8, 1]), 7)
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[-1]["phases"], [2, 3])
        self.assertEqual(len(batches[-1]["tasks"]), 9)

    def test_a_three_task_tail_is_not_folded(self):
        batches, _ = _batching.pack(_tasks([7, 3]), 7)
        self.assertEqual(len(batches), 2)
        self.assertEqual([len(b["tasks"]) for b in batches], [7, 3])

    def test_a_lone_batch_is_never_folded_away(self):
        batches, _ = _batching.pack(_tasks([2]), 7)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["phases"], [1])


class StageHomogeneity(unittest.TestCase):
    def test_different_effective_stages_never_share_a_batch(self):
        batches, _ = _batching.pack(
            _routed_tasks([3, 3], ["backend", "frontend"]), 7
        )
        self.assertEqual(
            [(batch["stage"], batch["phases"]) for batch in batches],
            [("backend", [1]), ("frontend", [2])],
        )

    def test_same_effective_stage_packs_normally(self):
        batches, _ = _batching.pack(
            _routed_tasks([3, 3], ["backend", "backend"]), 7
        )
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["phases"], [1, 2])
        self.assertEqual(batches[0]["stage"], "backend")

    def test_small_tail_is_not_folded_across_stage_boundary(self):
        batches, _ = _batching.pack(
            _routed_tasks([7, 2], ["backend", "docs"]), 7
        )
        self.assertEqual(
            [(batch["stage"], len(batch["tasks"])) for batch in batches],
            [("backend", 7), ("docs", 2)],
        )

    def test_legacy_tasks_default_to_implement_without_changing_batches(self):
        batches, _ = _batching.pack(_tasks([3, 3, 3, 3, 4, 4]), 7)
        self.assertEqual([len(batch["tasks"]) for batch in batches], [9, 7, 4])
        self.assertEqual([batch["stage"] for batch in batches], ["implement"] * 3)


class OversizedPhase(unittest.TestCase):
    """A phase over ~1.5x the budget is flagged, never silently split."""

    def test_an_oversized_phase_is_reported(self):
        _, oversized = _batching.pack(_tasks([11, 3]), 7)
        self.assertEqual(oversized, [1])

    def test_an_oversized_phase_is_not_split(self):
        batches, oversized = _batching.pack(_tasks([11, 3]), 7)
        self.assertEqual(oversized, [1])
        holding = [b for b in batches if 1 in b["phases"]]
        self.assertEqual(len(holding), 1)
        self.assertEqual(len(holding[0]["tasks"]), 11)

    def test_a_phase_at_or_below_the_threshold_is_not_flagged(self):
        # 1.5 x 7 = 10.5, so ten tasks in one phase is coarse but acceptable
        _, oversized = _batching.pack(_tasks([10, 3]), 7)
        self.assertEqual(oversized, [])

    def test_the_threshold_follows_the_configured_budget(self):
        # 1.5 x 4 = 6, so a seven-task phase is oversized at budget 4
        _, oversized = _batching.pack(_tasks([7, 2]), 4)
        self.assertEqual(oversized, [1])

    def test_several_oversized_phases_are_all_reported(self):
        _, oversized = _batching.pack(_tasks([11, 2, 12]), 7)
        self.assertEqual(oversized, [1, 3])


if __name__ == "__main__":
    unittest.main()
