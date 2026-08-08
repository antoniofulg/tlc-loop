"""Mutation tests for the three reused `tlc-spec-driven` validators (T25).

The loop delegates three of its gates to the sibling skill: `init_loop.py`
refuses to start on a `tasks.md` that `validate_tasks.py` rejects,
`checkpoint.py` refuses a message that `check_commit.py` rejects, and
`detect_phase.py` calls a feature done only when `validate_state.py` exits 0
(LOOP-02, LOOP-01). A gate that passes everything is worse than no gate,
because the loop reports it as evidence.

`validate_spec.py` was already found to pass vacuously by this exact method, so
the other three get the same treatment: feed each a deliberately invalid input
and require a non-zero exit, then feed each a valid one and require 0, so the
suite cannot pass by a validator that always fails.

Two findings are recorded below as characterization tests. They assert what the
validator **actually does**, not what it intends, and each one names the input
that slipped through. Fixing them belongs to the sibling skill, not here.

Every test skips with the paths it tried when the sibling skill is not
installed.
"""

import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

import _paths  # noqa: E402

#: Where the sibling is installed when this skill is being developed from a
#: checkout rather than from its installed location. `_paths` resolves the
#: side-by-side layout first; these are the documented install roots.
INSTALL_ROOTS = (
    os.path.expanduser("~/.agents/skills/tlc-spec-driven"),
    os.path.expanduser("~/.claude/skills/tlc-spec-driven"),
)


def sibling_script(name):
    """Absolute path of a sibling validator, or a clean skip explaining why not."""
    attempted = []
    try:
        return _paths.tlc_script(name)
    except _paths.SiblingSkillError as exc:
        attempted.append(str(exc))
    for base in INSTALL_ROOTS:
        candidate = os.path.join(base, "scripts", name)
        if os.path.isfile(candidate):
            return candidate
        attempted.append(candidate)
    raise unittest.SkipTest(
        f"the sibling skill tlc-spec-driven does not ship {name}, so its gate "
        f"cannot be mutation tested here. Tried: " + "; ".join(attempted)
    )


class ValidatorCase(unittest.TestCase):
    """Runs one sibling validator as a subprocess inside a tmpdir."""

    VALIDATOR = None

    @classmethod
    def setUpClass(cls):
        cls.script = sibling_script(cls.VALIDATOR)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def run_validator(self, *args):
        return subprocess.run(
            [sys.executable, self.script, *args], capture_output=True, text=True
        )

    def assert_rejects(self, proc, what, fixture):
        self.assertNotEqual(
            proc.returncode,
            0,
            f"{self.VALIDATOR} passed vacuously: it accepted {what}.\n"
            f"--- input that slipped through ---\n{fixture}\n"
            f"--- stdout ---\n{proc.stdout}",
        )

    def assert_accepts(self, proc, what):
        self.assertEqual(
            proc.returncode,
            0,
            f"{self.VALIDATOR} rejected {what}, so a non-zero exit proves "
            f"nothing about the invalid cases.\n{proc.stdout}\n{proc.stderr}",
        )


# --------------------------------------------------------------------------
# validate_tasks.py
# --------------------------------------------------------------------------

VALID_TASKS = """# demo Tasks

## Test Coverage Matrix

## Gate Check Commands

## Execution Plan

### Phase 1: Foundation

```
T1 -> T2
```

### Phase 2: Wiring

```
T3 -> T4
```

## Task Breakdown

### T1: One
**Where**: `scripts/one.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

### T2: Two
**Where**: `scripts/two.py`
**Depends on**: T1
**Tests**: unit
**Gate**: quick

### T3: Three
**Where**: `scripts/three.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

### T4: Four
**Where**: `scripts/four.py`
**Depends on**: T3
**Tests**: unit
**Gate**: quick
"""

# T1 sits in Phase 1 and depends on T4 from Phase 2 - a forward dependency the
# validator's own docstring promises to reject. The diagram carries the matching
# arrow so the parity check stays silent and the forward-dependency rule is the
# only thing under test.
FORWARD_DEP_TEMPLATE_LAYOUT = VALID_TASKS.replace(
    "```\nT1 -> T2\n```",
    "```\nT4 -> T1 -> T2\n```",
).replace(
    "### T1: One\n**Where**: `scripts/one.py`\n**Depends on**: None",
    "### T1: One\n**Where**: `scripts/one.py`\n**Depends on**: T4",
)

# The same forward dependency, in the layout where each task is defined inside
# its own phase section instead of a flat Task Breakdown.
FORWARD_DEP_TASKS_INSIDE_PHASES = """# demo Tasks

## Test Coverage Matrix

## Gate Check Commands

## Execution Plan

### Phase 1: Foundation

### T1: One
**Where**: `scripts/one.py`
**Depends on**: T4
**Tests**: unit
**Gate**: quick

### Phase 2: Wiring

### T4: Four
**Where**: `scripts/four.py`
**Depends on**: None
**Tests**: unit
**Gate**: quick

## Task Breakdown
"""


class ValidateTasks(ValidatorCase):
    VALIDATOR = "validate_tasks.py"

    def check(self, body):
        path = os.path.join(self.root, "tasks.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return self.run_validator(path)

    def test_a_conformant_tasks_md_is_accepted(self):
        self.assert_accepts(self.check(VALID_TASKS), "a conformant tasks.md")

    def test_a_missing_required_section_is_rejected(self):
        body = VALID_TASKS.replace("## Gate Check Commands\n", "")
        self.assert_rejects(self.check(body), "a tasks.md with no Gate Check Commands section", body)

    def test_a_task_missing_its_gate_field_is_rejected(self):
        body = VALID_TASKS.replace(
            "### T2: Two\n**Where**: `scripts/two.py`\n**Depends on**: T1\n"
            "**Tests**: unit\n**Gate**: quick",
            "### T2: Two\n**Where**: `scripts/two.py`\n**Depends on**: T1\n**Tests**: unit",
        )
        self.assert_rejects(self.check(body), "a task with no Gate field", body)

    def test_a_task_missing_its_tests_field_is_rejected(self):
        body = VALID_TASKS.replace(
            "### T3: Three\n**Where**: `scripts/three.py`\n**Depends on**: None\n"
            "**Tests**: unit\n**Gate**: quick",
            "### T3: Three\n**Where**: `scripts/three.py`\n**Depends on**: None\n**Gate**: quick",
        )
        self.assert_rejects(self.check(body), "a task with no Tests field", body)

    def test_a_diagram_edge_with_no_matching_dependency_is_rejected(self):
        body = VALID_TASKS.replace(
            "### T2: Two\n**Where**: `scripts/two.py`\n**Depends on**: T1",
            "### T2: Two\n**Where**: `scripts/two.py`\n**Depends on**: None",
        )
        self.assert_rejects(
            self.check(body), "a diagram arrow T1 -> T2 that no Depends on declares", body
        )

    def test_a_forward_phase_dependency_is_rejected_when_tasks_sit_inside_phases(self):
        proc = self.check(FORWARD_DEP_TASKS_INSIDE_PHASES)
        self.assert_rejects(
            proc, "T1 in Phase 1 depending on T4 in Phase 2", FORWARD_DEP_TASKS_INSIDE_PHASES
        )
        self.assertIn("must point backward", proc.stdout)

    def test_the_standard_template_layout_hides_a_forward_phase_dependency(self):
        """FINDING: the forward-dependency check is vacuous under the template.

        `parse_phase_membership` maps a task to a phase only when the task's own
        `### TN:` header appears after a `### Phase N` header, and it never
        leaves phase mode. The standard template declares the phases with
        diagrams in the Execution Plan and then defines every task in one flat
        Task Breakdown afterwards, so every task is attributed to the LAST phase
        heading in the file. Same phase for everything means `p_dep > p_here` is
        never true, and the check cannot fire on any file the template produced.

        The input that slips through is `FORWARD_DEP_TEMPLATE_LAYOUT`: T1 lives
        in Phase 1 and declares `Depends on: T4`, which lives in Phase 2. The
        previous test proves the rule works when the layout lets it, so this is
        a phase-attribution defect, not a missing rule.
        """
        proc = self.check(FORWARD_DEP_TEMPLATE_LAYOUT)
        self.assertEqual(
            proc.returncode,
            0,
            "the forward-dependency defect appears to be fixed; delete this "
            "characterization test and assert the rejection instead",
        )
        self.assertNotIn("must point backward", proc.stdout)

    def test_an_empty_tests_field_counts_as_present(self):
        """FINDING: `Tests:` with no value satisfies the field-presence check.

        The check is `t["tests"] is None`, and a field parsed from `**Tests**:`
        yields `""`, which is not None. A task that names no test type is
        therefore indistinguishable from one that does, and even the
        `Tests: none` warning does not fire.
        """
        body = VALID_TASKS.replace("### T4: Four\n"
                                   "**Where**: `scripts/four.py`\n"
                                   "**Depends on**: T3\n"
                                   "**Tests**: unit",
                                   "### T4: Four\n"
                                   "**Where**: `scripts/four.py`\n"
                                   "**Depends on**: T3\n"
                                   "**Tests**:")
        proc = self.check(body)
        self.assertEqual(
            proc.returncode,
            0,
            "the empty-Tests-field gap appears to be fixed; delete this "
            "characterization test and assert the rejection instead",
        )
        self.assertNotIn("missing `Tests`", proc.stdout)


# --------------------------------------------------------------------------
# check_commit.py
# --------------------------------------------------------------------------


class CheckCommit(ValidatorCase):
    VALIDATOR = "check_commit.py"

    def check(self, message):
        return self.run_validator("--message", message)

    def test_a_conventional_commits_message_is_accepted(self):
        self.assert_accepts(
            self.check("feat(loop): add the thing"), "a conforming Conventional Commits header"
        )

    def test_a_message_with_a_body_and_trailers_is_accepted(self):
        message = "fix(loop): stop the spin\n\nTask: T7\nGate: quick PASS"
        self.assert_accepts(self.check(message), "a conforming header with a body and trailers")

    def test_a_non_conventional_header_is_rejected(self):
        self.assert_rejects(self.check("Added The Thing."), "a prose header", "Added The Thing.")

    def test_an_unknown_type_is_rejected(self):
        self.assert_rejects(self.check("wip(loop): add the thing"), "the type 'wip'", "wip(loop): add the thing")

    def test_an_uppercase_description_is_rejected(self):
        self.assert_rejects(
            self.check("feat(loop): Add the thing"), "an uppercase description", "feat(loop): Add the thing"
        )

    def test_a_trailing_period_is_rejected(self):
        self.assert_rejects(
            self.check("feat(loop): add the thing."), "a description ending in a period", "feat(loop): add the thing."
        )

    def test_a_breaking_marker_without_its_footer_is_rejected(self):
        message = "feat(loop)!: change the detect contract"
        self.assert_rejects(self.check(message), "a '!' marker with no BREAKING CHANGE footer", message)

    def test_an_empty_message_is_rejected(self):
        self.assert_rejects(self.check(""), "an empty message", "")


# --------------------------------------------------------------------------
# validate_state.py
# --------------------------------------------------------------------------

PASS_REPORT = """## Validation: demo - PASS

Per-AC evidence: `scripts/detect_phase.py:112` asserts the bootstrap line.
"""


class ValidateState(ValidatorCase):
    VALIDATOR = "validate_state.py"

    def setUp(self):
        super().setUp()
        self.feature_dir = os.path.join(self.root, ".specs", "features", "demo")
        os.makedirs(self.feature_dir)
        with open(os.path.join(self.feature_dir, "tasks.md"), "w", encoding="utf-8") as fh:
            fh.write("# demo Tasks\n\n### T1: One\n**Tests**: unit\n**Gate**: quick\n")

    def check(self, report=None):
        path = os.path.join(self.feature_dir, "validation.md")
        if report is None:
            if os.path.exists(path):
                os.unlink(path)
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(report)
        return self.run_validator("demo", "--root", self.root)

    def test_a_filled_pass_report_with_evidence_is_accepted(self):
        self.assert_accepts(self.check(PASS_REPORT), "a filled PASS report citing file:line evidence")

    def test_a_missing_report_is_rejected(self):
        self.assert_rejects(self.check(None), "a feature with no validation.md at all", "<no validation.md>")

    def test_a_fail_verdict_is_rejected(self):
        report = PASS_REPORT.replace("PASS", "FAIL")
        self.assert_rejects(self.check(report), "a FAIL verdict", report)

    def test_an_unfilled_template_verdict_is_rejected(self):
        report = PASS_REPORT.replace("PASS", "[PASS | FAIL]")
        self.assert_rejects(self.check(report), "the unfilled '[PASS | FAIL]' placeholder", report)

    def test_a_pass_with_no_file_line_evidence_is_rejected(self):
        report = "## Validation: demo - PASS\n\nEverything looks good to me.\n"
        self.assert_rejects(
            self.check(report), "a PASS report citing no file:line evidence", report
        )

    def test_a_report_with_no_verdict_at_all_is_rejected(self):
        report = "## Validation: demo\n\nThe tests were run and the code looks fine.\n"
        self.assert_rejects(self.check(report), "a prose report with no verdict", report)

    def test_an_empty_report_is_rejected(self):
        self.assert_rejects(self.check(""), "an empty validation.md", "<empty file>")


if __name__ == "__main__":
    unittest.main()
