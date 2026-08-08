"""Unit tests for _tasksmd - the tasks.md reader (T6, LOOP-01).

Derived from T6's "Done when" criteria. Phase membership is the load-bearing
part: T7 packs batches out of it and T8 prints it, so both tasks.md layouts a
feature can legitimately use are covered here.
"""

import os
import tempfile
import unittest

import _tasksmd

FENCE = "```"

# Layout A: phases declared with diagrams in an Execution Plan, every task
# defined afterwards in a flat Task Breakdown. This is the layout
# tlc-spec-driven's own tasks.md template produces.
LAYOUT_A = f"""# demo Tasks

## Execution Plan

### Phase 1: Foundation

{FENCE}
T1
T2 -> T3
{FENCE}

### Phase 2: Detection

{FENCE}
T4 -> T5
{FENCE}

---

## Task Breakdown

### T1: First thing

**Where**: `scripts/a.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

---

### T2: Second thing

**Where**: `scripts/b.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

---

### T3: Third thing

**Where**: `scripts/c.py`
**Depends on**: T2
**Tests**: unit
**Gate**: quick

---

### T4: Fourth thing

**Where**: `scripts/d.py`
**Depends on**: None
**Tests**: integration
**Gate**: full

---

### T5: Fifth thing

**Where**: `scripts/e.py`
**Depends on**: T4, T2
**Tests**: none
**Gate**: build
"""

# Layout B: each task defined directly under its phase heading.
LAYOUT_B = """# demo Tasks

### Phase 1: Foundation

### T1: First thing

Depends on: None
Tests: unit
Gate: quick

### Phase 2: Detection

### T2: Second thing

Depends on: T1
Tests: unit
Gate: quick
"""


def _write(text):
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    )
    handle.write(text)
    handle.close()
    return handle.name


class MultiPhaseFile(unittest.TestCase):
    def setUp(self):
        self.path = _write(LAYOUT_A)
        self.addCleanup(os.unlink, self.path)
        self.tasks = _tasksmd.parse(self.path)

    def test_returns_tasks_in_document_order(self):
        self.assertEqual([t["id"] for t in self.tasks], ["T1", "T2", "T3", "T4", "T5"])

    def test_phase_membership_comes_from_the_phase_headings(self):
        self.assertEqual(
            {t["id"]: t["phase"] for t in self.tasks},
            {"T1": 1, "T2": 1, "T3": 1, "T4": 2, "T5": 2},
        )

    def test_depends_on_is_a_list_of_task_ids(self):
        by_id = {t["id"]: t for t in self.tasks}
        self.assertEqual(by_id["T3"]["depends_on"], ["T2"])
        self.assertEqual(by_id["T5"]["depends_on"], ["T4", "T2"])

    def test_depends_on_none_is_an_empty_list(self):
        by_id = {t["id"]: t for t in self.tasks}
        self.assertEqual(by_id["T1"]["depends_on"], [])

    def test_tests_and_gate_are_captured(self):
        by_id = {t["id"]: t for t in self.tasks}
        self.assertEqual(by_id["T1"]["tests"], "unit")
        self.assertEqual(by_id["T1"]["gate"], "quick")
        self.assertEqual(by_id["T4"]["tests"], "integration")
        self.assertEqual(by_id["T4"]["gate"], "full")
        self.assertEqual(by_id["T5"]["tests"], "none")
        self.assertEqual(by_id["T5"]["gate"], "build")


class TasksDefinedUnderPhaseHeadings(unittest.TestCase):
    def test_phase_membership_still_resolves(self):
        path = _write(LAYOUT_B)
        self.addCleanup(os.unlink, path)
        tasks = _tasksmd.parse(path)
        self.assertEqual({t["id"]: t["phase"] for t in tasks}, {"T1": 1, "T2": 2})


class BoldMarkerVariations(unittest.TestCase):
    def test_fields_parse_with_and_without_bold_markers(self):
        path = _write(
            "### Phase 1: Only\n\n"
            "### T1: Bold\n\n"
            "**Depends on**: None\n**Tests**: unit\n**Gate**: quick\n\n"
            "### T2: Plain\n\n"
            "Depends on: T1\nTests: unit\nGate: build\n"
        )
        self.addCleanup(os.unlink, path)
        by_id = {t["id"]: t for t in _tasksmd.parse(path)}
        self.assertEqual(by_id["T1"]["tests"], "unit")
        self.assertEqual(by_id["T1"]["gate"], "quick")
        self.assertEqual(by_id["T2"]["depends_on"], ["T1"])
        self.assertEqual(by_id["T2"]["gate"], "build")


class MissingOptionalField(unittest.TestCase):
    def test_absent_fields_are_none_and_absent_depends_on_is_empty(self):
        path = _write("### Phase 1: Only\n\n### T1: Bare\n\n**Where**: `scripts/a.py`\n")
        self.addCleanup(os.unlink, path)
        task = _tasksmd.parse(path)[0]
        self.assertEqual(task["id"], "T1")
        self.assertIsNone(task["tests"])
        self.assertIsNone(task["gate"])
        self.assertEqual(task["depends_on"], [])

    def test_a_task_outside_any_phase_has_phase_none(self):
        path = _write("### T1: Orphan\n\n**Tests**: unit\n**Gate**: quick\n")
        self.addCleanup(os.unlink, path)
        self.assertIsNone(_tasksmd.parse(path)[0]["phase"])


class CompletionTick(unittest.TestCase):
    """T31 / LOOP-01 AC 5: the human tick is read so git can contradict it.

    `tasks.md` has no status field. The tick on a task header is the closest
    thing to one, and reading it is what lets `detect_phase.py` notice that the
    plan and git disagree. It never marks a task done on its own.
    """

    def parse(self, text):
        path = _write(text)
        self.addCleanup(os.unlink, path)
        return {t["id"]: t for t in _tasksmd.parse(path)}

    def test_a_ticked_header_is_done(self):
        by_id = self.parse("### Phase 1: Only\n\n### T1: Shipped ✅\n\n**Gate**: quick\n")
        self.assertTrue(by_id["T1"]["done"])

    def test_an_unticked_header_is_not_done(self):
        by_id = self.parse("### Phase 1: Only\n\n### T1: Pending\n\n**Gate**: quick\n")
        self.assertFalse(by_id["T1"]["done"])

    def test_the_tick_is_per_task_not_per_file(self):
        by_id = self.parse(
            "### Phase 1: Only\n\n"
            "### T1: Shipped ✅\n\n**Gate**: quick\n\n"
            "### T2: Pending\n\n**Gate**: quick\n"
        )
        self.assertEqual(
            {task_id: task["done"] for task_id, task in by_id.items()},
            {"T1": True, "T2": False},
        )

    def test_a_tick_in_the_body_is_not_a_completion_claim(self):
        # Done-when checkboxes and prose ticks are acceptance criteria, not
        # task state, so only the header carries the claim.
        by_id = self.parse(
            "### Phase 1: Only\n\n### T1: Pending\n\n- [x] ✅ a criterion\n**Gate**: quick\n"
        )
        self.assertFalse(by_id["T1"]["done"])


class EmptyFile(unittest.TestCase):
    def test_a_file_with_no_tasks_returns_an_empty_list(self):
        path = _write("# demo Tasks\n\nNothing here yet.\n")
        self.addCleanup(os.unlink, path)
        self.assertEqual(_tasksmd.parse(path), [])

    def test_a_completely_empty_file_returns_an_empty_list(self):
        path = _write("")
        self.addCleanup(os.unlink, path)
        self.assertEqual(_tasksmd.parse(path), [])


if __name__ == "__main__":
    unittest.main()
