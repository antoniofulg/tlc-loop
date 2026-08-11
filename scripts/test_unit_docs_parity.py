"""Parity between the shipped prose and the code it describes (T33, LOOP-06).

Five checks live here. The first is the halt vocabulary; the second (T38) is
the claim about what deleting `loop.json` costs, which drifted through three
verification rounds because each fix chased the citations it was handed instead
of searching the repository. The third (T42) is the no-diff contract, which
drifted the same way for the same reason - and got past the second check,
because a scanner that matches phrasings cannot see a paragraph explaining a
mechanism that no longer exists. Both fixes are here so the next one has
somewhere obvious to go. The fourth is the README's configuration surface,
which lists every `[limits]` key the loop reads: a table that omits a real
setting is read as proof the setting does not exist. The fifth is the README's
stage examples against the shipped `loop.config.example.toml` - the README
claims they are the same configuration, and they had already drifted by one
`effort` key when the check was written.

The halt vocabulary is enumerated in three places: `update_loop.HALT_REASONS`,
the Phase H branch of `SKILL.md`, and the field shapes in
`references/phase-transitions.md`. The constant is the source of truth; the two
documents are what an agent actually reads at runtime, so a document that
under-describes the vocabulary is a real defect and not a typo.

This file exists because the check it performs was once performed by hand. T21
ran it once, T28 and T29 then added `state_corrupt` and `verify_exhausted`, and
nothing re-ran it - so `SKILL.md` shipped a six-reason list against an
eight-reason implementation for two tasks and a full verification round. A
one-time check cannot notice drift that happens after it runs. This one runs on
every gate.

`references/state-schema.md` is deliberately out of scope: its halt table
enumerates the reasons that are *stored* in `loop.json` and documents its own
exclusions, which is a different claim from "this is the vocabulary".
"""

import os
import re
import sys
import tomllib
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import _config  # noqa: E402
import update_loop  # noqa: E402

#: Where each document enumerates the vocabulary, the phrase that anchors it,
#: and what ends the enumeration. Prose runs to the end of its sentence; a table
#: runs to the blank line that closes it.
ENUMERATIONS = (
    ("SKILL.md", "Implemented reasons:", ".\n"),
    ("references/phase-transitions.md", "`reason=<slug>` is one of", ".\n"),
    ("README.md", "| Reason | Meaning |", "\n\n"),
)

BACKTICKED = re.compile(r"`([a-z_]+)`")

#: The row of the README's configuration-surface table that names every
#: `[limits]` key. It is a copy of `_config.LIMIT_KEYS`, so it comes under the
#: same gate as the halt table: a limit the code reads and the surface omits
#: reads as "there is no such setting", which is the one mistake this table is
#: there to prevent.
LIMITS_ROW = "| `[limits]` | "


def documented_reasons(relative_path, anchor, terminator=".\n"):
    """Return the reasons a document enumerates after `anchor`.

    Raises if the anchor is gone, so a rewrite that drops the enumeration fails
    loudly instead of comparing against an empty list.
    """
    path = os.path.join(ROOT, relative_path)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start = text.find(anchor)
    if start < 0:
        raise AssertionError(
            f"{relative_path}: the halt-reason enumeration anchored on "
            f"{anchor!r} is gone; parity can no longer be checked"
        )
    sentence = text[start + len(anchor):]
    end = sentence.find(terminator)
    if end < 0:
        raise AssertionError(
            f"{relative_path}: the enumeration after {anchor!r} is not closed "
            f"by {terminator!r}; parity can no longer be checked"
        )
    return BACKTICKED.findall(sentence[:end])


def assert_parity(relative_path, documented):
    """Compare one document's enumeration against `update_loop.HALT_REASONS`."""
    implemented = set(update_loop.HALT_REASONS)
    missing = sorted(implemented - set(documented))
    extra = sorted(set(documented) - implemented)
    if missing:
        raise AssertionError(
            f"{relative_path} does not document halt reason(s) the code "
            f"implements: {', '.join(missing)}"
        )
    if extra:
        raise AssertionError(
            f"{relative_path} documents halt reason(s) the code does not "
            f"implement: {', '.join(extra)}"
        )


def documented_limit_keys():
    """Return the `[limits]` keys the README's configuration surface names."""
    path = os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start = text.find(LIMITS_ROW)
    if start < 0:
        raise AssertionError(
            f"README.md: the configuration-surface row anchored on "
            f"{LIMITS_ROW!r} is gone; parity can no longer be checked"
        )
    row = text[start + len(LIMITS_ROW):text.find("\n", start)]
    return BACKTICKED.findall(row)


class ConfigSurfaceParity(unittest.TestCase):
    """The README's configuration table names exactly the implemented limits."""

    def test_readme_names_exactly_the_implemented_limit_keys(self):
        self.assertEqual(
            sorted(documented_limit_keys()), sorted(_config.LIMIT_KEYS)
        )


class HaltReasonParity(unittest.TestCase):
    """Every reason the code can print is named in the prose, and vice versa."""

    def test_skill_md_enumerates_exactly_the_implemented_reasons(self):
        assert_parity("SKILL.md", documented_reasons(*ENUMERATIONS[0]))

    def test_phase_transitions_enumerates_exactly_the_implemented_reasons(self):
        assert_parity("references/phase-transitions.md", documented_reasons(*ENUMERATIONS[1]))

    def test_readme_enumerates_exactly_the_implemented_reasons(self):
        # The README's halt table is a third copy of the vocabulary. Accurate
        # when written is not the bar - it has to stay accurate, which is what
        # brings it under the same gate as the other two.
        assert_parity("README.md", documented_reasons(*ENUMERATIONS[2]))

    def test_every_documented_enumeration_is_locatable(self):
        for entry in ENUMERATIONS:
            with self.subTest(document=entry[0]):
                self.assertTrue(documented_reasons(*entry))


#: Phrasings of the over-broad claim about deleting `loop.json`. Each one was
#: shipped and each one was false: the file also holds the objective, every
#: limit budget, the verify rounds, a recorded halt, and the audit trails.
#: `references/state-schema.md` itemises the real bill; these are the ways of
#: saying "and nothing else matters" that must not come back.
RETRACTED_CLAIMS = (
    "never task progress",
    "costs counters",
    "costs the counters",
    "nothing is stranded",
    # Unqualified: the file is disposable for task progress and for nothing
    # else, so the bare adjective always over-claims.
    "disposable",
)

#: This file is the one exemption: it holds the needle lists, so every claim
#: below appears in it by construction.
SCANNER = "scripts/test_unit_docs_parity.py"


#: The surface an agent actually reads at runtime, plus the source that
#: describes itself. Test docstrings and `.gitignore` are in scope because they
#: are shipped and readable, and round 5 found the retracted claim alive in
#: both. Deliberately excludes `.specs/`: `validation.md` quotes the false
#: claims as findings, `tasks.md` quotes them as criteria, and `LESSONS.md`
#: quotes them as the lesson.
def shipped_documents():
    """Every shipped document and script, as `(relative_path, text)`."""
    found = ["SKILL.md", "README.md", ".gitignore"]
    for directory in ("references", "assets", "scripts"):
        for name in sorted(os.listdir(os.path.join(ROOT, directory))):
            if name.endswith((".md", ".py", ".sh", ".toml")):
                found.append(f"{directory}/{name}")
    for relative in found:
        if relative == SCANNER:
            continue
        with open(os.path.join(ROOT, relative), encoding="utf-8") as handle:
            yield relative, handle.read()


def offending_lines(text, claim):
    """`(line number, line)` for each line containing `claim`, case-insensitive."""
    needle = claim.lower()
    return [
        (number, line.strip())
        for number, line in enumerate(text.splitlines(), start=1)
        if needle in line.lower()
    ]


class DeletingTheStateFileIsNotFree(unittest.TestCase):
    """T38: no shipped document may re-assert the retracted claim.

    Task progress survives deleting `loop.json`; everything else in the file
    does not. A sentence that says only the first half reads as a guarantee,
    and an agent deciding at 3am whether reconstruction is safe acts on it.
    """

    def test_no_shipped_document_repeats_a_retracted_claim(self):
        offenders = []
        for relative, text in shipped_documents():
            for claim in RETRACTED_CLAIMS:
                for number, line in offending_lines(text, claim):
                    offenders.append(f"{relative}:{number} ({claim!r}): {line}")
        self.assertEqual(
            offenders,
            [],
            "these lines re-assert what deleting loop.json costs; "
            "references/state-schema.md itemises the real bill:\n"
            + "\n".join(offenders),
        )

    def test_the_scan_actually_reaches_the_documents(self):
        # A scan over an empty file list passes vacuously, which is the one way
        # this check could stop working without anyone noticing.
        scanned = [relative for relative, _ in shipped_documents()]
        for expected in (
            "SKILL.md",
            "README.md",
            "references/state-schema.md",
            "references/phase-transitions.md",
            "scripts/detect_phase.py",
            "scripts/_state_io.py",
        ):
            self.assertIn(expected, scanned)

    def test_a_reintroduced_claim_is_named_with_its_location(self):
        planted = "It is also disposable: deleting it costs the counters.\n"
        offenders = [
            f"fake.md:{number} ({claim!r}): {line}"
            for claim in RETRACTED_CLAIMS
            for number, line in offending_lines(planted, claim)
        ]
        self.assertTrue(offenders)
        self.assertIn("fake.md:1", offenders[0])

    def test_state_schema_says_what_deleting_the_file_does_cost(self):
        # Retraction without replacement leaves the reader with nothing, which
        # is how the claim came back the last two times.
        path = os.path.join(ROOT, "references", "state-schema.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("## What deleting the file costs", text)
        for field in ("objective", "counters", "verified_at", "halt", "reconciled"):
            self.assertIn(field, text.split("## What deleting the file costs", 1)[1])


#: Sentences that describe how a no-diff task used to be recorded. T37 inverted
#: that contract - such a task is now committed empty and carries the same
#: `Task:` and `Gate:` trailers as any other - so each of these is now false.
#: They are not slogans, which is why the claim scanner above walked past them
#: through a whole verification round: they are the mechanism, written out.
RETIRED_MECHANISM_CLAIMS = (
    "therefore no trailer",
    "carries no trailer",
    "produced no commit",
    "recorded in `no_diff_tasks`",
)

#: How far from a `no_diff_tasks` mention the word "legacy" may sit. Same
#: sentence, same table row, or the paragraph directly under a heading.
LEGACY_WINDOW = 4


def markdown_documents():
    """The shipped prose only. Code that reads the field is not describing it."""
    for relative, text in shipped_documents():
        if relative.endswith(".md"):
            yield relative, text


def read_shipped(relative_path):
    with open(os.path.join(ROOT, relative_path), encoding="utf-8") as handle:
        return handle.read()


class StageRoutingContractParity(unittest.TestCase):
    """Public docs preserve the handoff and runtime routing vocabulary."""

    def test_the_tasks_handoff_is_self_contained(self):
        text = read_shipped("references/tasks-routing-contract.md")
        for required in (
            "$tlc-spec-driven",
            "$tlc-loop",
            "**Stage:**",
            "strict_routing",
            "validate_tasks.py",
            "validate_routing.py",
            "foundation",
            "backend",
            "frontend",
            "docs",
            "verify",
            "fix",
        ):
            self.assertIn(required, text)

    def test_the_runtime_docs_use_the_detected_stage(self):
        skill = read_shipped("SKILL.md")
        transitions = read_shipped("references/phase-transitions.md")
        checklist = read_shipped("references/checklist.md")
        self.assertIn("tasks-routing-contract.md", skill)
        self.assertIn("--stage <stage-from-detect-line>", skill)
        self.assertIn("tasks=<ids> stage=<effective-stage>", transitions)
        self.assertIn("stage=", checklist)

    def test_config_docs_describe_domain_stages_and_strict_routing(self):
        schema = read_shipped("references/config-schema.md")
        example = read_shipped("assets/loop.config.example.toml")
        self.assertNotIn("Three stages exist", schema)
        for text in (schema, example):
            self.assertIn("strict_routing", text)
            self.assertIn("stages.backend", text)
            self.assertIn("stages.frontend", text)

    def test_readme_shows_the_short_dual_skill_invocation(self):
        readme = read_shipped("README.md")
        self.assertIn("$tlc-spec-driven", readme)
        self.assertIn("$tlc-loop", readme)
        self.assertIn("validate_routing.py", readme)


#: Phrasings that send the reader to an editor to lift a halt. The transition
#: table shipped one for two releases: a halt cleared "by a human resolving the
#: cause and clearing `halt.reason`", while `state-schema.md` said the file is
#: machine-owned and must not be hand-edited. A reader who followed the first
#: literally had to break the second, and `update_loop.py --resume` is the
#: transition that makes both true at once.
HAND_CLEARED_HALT = (
    "clearing `halt.reason`",
    "clearing halt.reason",
    "clear `halt.reason`",
    "clear halt.reason",
)


class ClearingAHaltHasOneSupportedRoute(unittest.TestCase):
    """RESUME-06: the prose points at the flag, never at an editor."""

    def test_no_shipped_document_sends_the_reader_to_the_field(self):
        offenders = []
        for relative, text in shipped_documents():
            for claim in HAND_CLEARED_HALT:
                for number, line in offending_lines(text, claim):
                    offenders.append(f"{relative}:{number} ({claim!r}): {line}")
        self.assertEqual(
            offenders,
            [],
            "these lines tell a reader to lift a halt by hand; `loop.json` is "
            "machine-owned and `update_loop.py --resume` is the transition:\n"
            + "\n".join(offenders),
        )

    def test_a_reintroduced_instruction_is_named_with_its_location(self):
        planted = "A halt clears only by a human clearing `halt.reason`.\n"
        offenders = [
            f"fake.md:{number} ({claim!r}): {line}"
            for claim in HAND_CLEARED_HALT
            for number, line in offending_lines(planted, claim)
        ]
        self.assertTrue(offenders)
        self.assertIn("fake.md:1", offenders[0])

    # Retraction without replacement leaves the reader with nothing, which is
    # how the hand-edit instruction survived a rewrite the last time. Each
    # check is scoped to the passage its criterion names: the flag being
    # present *somewhere* in the file is not what any of them ask for, and a
    # whole-file search passed while the mention sat in an unrelated section.

    def test_the_transition_row_names_the_command(self):
        row = table_row(
            read_shipped("references/phase-transitions.md"),
            "| `H` |",
            "references/phase-transitions.md",
        )
        self.assertIn(
            "update_loop.py --resume",
            row,
            "the H transition row says how a halt clears without naming the "
            "command that clears it",
        )

    def test_the_halt_field_section_names_the_command(self):
        body = section(
            read_shipped("references/state-schema.md"), "## `halt`", "references/state-schema.md"
        )
        self.assertIn(
            "update_loop.py <feature> --root <root> --resume",
            collapsed(body),
            "the `halt` field section does not carry the command that clears it",
        )

    def test_the_halt_phase_names_the_command(self):
        body = section(read_shipped("SKILL.md"), "#### Phase H - Halt", "SKILL.md")
        self.assertIn(
            "update_loop.py <feature> --root <root> --resume",
            collapsed(body),
            "Phase H does not carry the command a human runs to lift the halt "
            "it just recorded; naming the flag in passing is not the same thing",
        )

    def test_each_scope_excludes_the_passage_that_follows_it(self):
        # The check that makes the three above mean anything: a scan running to
        # the end of the file would pass on a mention in any later section.
        skill = section(read_shipped("SKILL.md"), "#### Phase H - Halt", "SKILL.md")
        self.assertIn("blast_radius", skill)
        self.assertNotIn("### Step 3", skill)
        schema = section(
            read_shipped("references/state-schema.md"), "## `halt`", "references/state-schema.md"
        )
        self.assertIn("blast_radius", schema)
        self.assertNotIn("## `iterations[]`", schema)
        # `table_row` cannot silently pick between candidates: a decoy row
        # planted above the real one would otherwise answer for it.
        transitions = read_shipped("references/phase-transitions.md")
        decoyed = transitions.replace("| `H` |", "| `H` | a decoy |\n| `H` |", 1)
        with self.assertRaises(AssertionError):
            table_row(decoyed, "| `H` |", "references/phase-transitions.md")


def section(text, heading, where):
    """The body of one section, from `heading` to the next heading of its level.

    Scoped rather than whole-file. An instruction that drifts into a
    neighbouring section still satisfies a search over the whole document, so a
    whole-file check cannot tell "documented here" from "documented somewhere",
    which is the only thing these criteria actually ask.
    """
    start = text.find(heading)
    if start < 0:
        raise AssertionError(f"{where}: the section anchored on {heading!r} is gone")
    # Ends at the next heading of the same level *or shallower*. Stopping only
    # at the same level would run a last-child section to end of file, which is
    # no scope at all - the one `#### Phase H` hit before this was fixed.
    level = len(heading) - len(heading.lstrip("#"))
    rest = text[start + len(heading):]
    ends = [found for found in
            (rest.find("\n" + "#" * depth + " ") for depth in range(1, level + 1))
            if found >= 0]
    return heading + rest[:min(ends)] if ends else heading + rest


def collapsed(text):
    """`text` with line continuations and indentation flattened to one space.

    A criterion that names a whole command is not met by the flag appearing in
    a nearby sentence, and the command itself is wrapped across lines with a
    backslash. Flattening lets the assertion be the command.
    """
    return re.sub(r"\s*\\?\s+", " ", text)


def table_row(text, prefix, where):
    """The one table row starting with `prefix`.

    Raises on more than one match rather than taking the first: a second row
    with the same prefix could answer for the real one, and which of them the
    scan reads would be decided by document order.
    """
    rows = [line for line in text.splitlines() if line.startswith(prefix)]
    if len(rows) != 1:
        raise AssertionError(
            f"{where}: expected exactly one table row starting {prefix!r}, found {len(rows)}"
        )
    return rows[0]


class GateAttemptHasADocumentedWriter(unittest.TestCase):
    """RESUME-05: `counters.gate_attempts` is written by exactly one step.

    `limits.gate_attempts_per_task` halts on this counter, so an instruction
    set that never writes it leaves the limit bounding nothing. That is how a
    `gate_stuck` halt arrives with an empty counter: the limit never fired, so
    a human recorded the halt by hand.
    """

    def test_skill_md_names_the_call_that_records_a_failed_gate(self):
        self.assertIn(
            "--gate-attempt",
            read_shipped("SKILL.md"),
            "SKILL.md no longer names --gate-attempt, so counters.gate_attempts "
            "has no documented writer and limits.gate_attempts_per_task bounds nothing",
        )

    def test_the_call_sits_in_the_phase_that_runs_the_gate(self):
        body = section(read_shipped("SKILL.md"), "#### Phase B - Execute one batch", "SKILL.md")
        self.assertIn(
            "update_loop.py <feature> --root <root> --gate-attempt",
            collapsed(body),
            "SKILL.md does not record a failed gate in Phase B, the only phase "
            "that runs one",
        )

    def test_the_recovery_loop_carves_the_exception_in_both_rules(self):
        # Two separate sentences forbade the write: "no counter moves" in the
        # opening, and "never calls update_loop.py" in step 1. An exception
        # stated in only one of them leaves the other still forbidding it.
        text = read_shipped("references/recovery-loop.md")
        head, _, body = text.partition("## Repair loop")
        for section, where in (
            (head, "the repairable-by-default rule"),
            (body, "step 1 of the repair loop"),
        ):
            self.assertIn(
                "--gate-attempt",
                section,
                f"references/recovery-loop.md: {where} still forbids the one "
                "counter write Phase B requires",
            )

    def test_the_partition_separates_the_two_rules_it_checks(self):
        text = read_shipped("references/recovery-loop.md")
        head, separator, body = text.partition("## Repair loop")
        self.assertTrue(separator, "the '## Repair loop' heading is gone")
        self.assertIn("no counter moves", head)
        self.assertIn("never calls", body)

    def test_the_section_scan_stops_at_the_next_phase(self):
        # A scan that ran to the end of the file would pass on a mention in any
        # later branch, which is exactly the drift it is meant to catch.
        body = section(read_shipped("SKILL.md"), "#### Phase B - Execute one batch", "SKILL.md")
        self.assertIn("checkpoint.py", body)
        self.assertNotIn("#### Phase V", body)


#: The two `[stages.*]` examples in the README, by something only that block
#: contains. The Configuration block carries the runtime stages; the Quick start
#: block carries the domain stages a reader copies first.
CONFIG_EXAMPLE = "[stages.implement]"
QUICKSTART_EXAMPLE = "strict_routing = true"


def toml_block_containing(relative_path, anchor):
    """Parse the fenced ```toml block of a document that contains `anchor`."""
    blocks = re.findall(r"```toml\n(.*?)```", read_shipped(relative_path), re.DOTALL)
    for block in blocks:
        if anchor in block:
            return tomllib.loads(block)
    raise AssertionError(
        f"{relative_path}: none of its {len(blocks)} toml block(s) contains "
        f"{anchor!r}; the example is gone and parity can no longer be checked"
    )


class StageExampleParity(unittest.TestCase):
    """The README's stage examples are the shipped example file, not a variant.

    The README says so in prose, which is what makes them copies rather than
    illustrations. A copy that drifts documents a configuration nobody ran -
    `[stages.foundation]` had already lost its `effort` this way.
    """

    def setUp(self):
        self.shipped = tomllib.loads(read_shipped("assets/loop.config.example.toml"))

    def test_the_configuration_example_matches_the_shipped_file(self):
        readme = toml_block_containing("README.md", CONFIG_EXAMPLE)
        self.assertEqual(readme["stages"], self.shipped["stages"])

    def test_the_quick_start_example_agrees_on_every_stage_it_shows(self):
        # A subset by design: Quick start shows the domain stages only, and
        # omitting one is a teaching choice. Contradicting one is not.
        readme = toml_block_containing("README.md", QUICKSTART_EXAMPLE)
        self.assertTrue(readme["stages"], "the quick start example shows no stage")
        for stage, configured in readme["stages"].items():
            self.assertEqual(configured, self.shipped["stages"][stage], stage)


def _fenced(lines):
    """Indices inside a fenced code block. A JSON example is not a claim."""
    inside = False
    fenced = set()
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            inside = not inside
            fenced.add(index)
        elif inside:
            fenced.add(index)
    return fenced


def unmarked_legacy_mentions(text, window=LEGACY_WINDOW):
    """`(line number, line)` for each `no_diff_tasks` mention not marked legacy."""
    lines = text.splitlines()
    fenced = _fenced(lines)
    unmarked = []
    for index, line in enumerate(lines):
        if index in fenced or "no_diff_tasks" not in line:
            continue
        near = lines[max(0, index - window):index + window + 1]
        if not any("legacy" in neighbour.lower() for neighbour in near):
            unmarked.append((index + 1, line.strip()))
    return unmarked


class TheNoDiffContractIsDescribedAsItIs(unittest.TestCase):
    """T42: no shipped document may describe the mechanism T37 retired.

    A task that changes nothing is committed empty and carries its trailers like
    any other. `no_diff_tasks` is read, never written, and kept only for a run
    that was already in flight. A document still teaching the old mechanism sends
    an agent looking for a task completion that git will not have.

    **This is a backstop, not the mechanism** (T45). The claim came back false a
    fourth time in wording that trips none of the needles below, because the
    same falsehood is always expressible another way - so the list was never
    going to be complete. What prevents recurrence is that the contract is now
    explained in exactly one place, `references/state-schema.md` under "The
    no-diff contract", and every other mention is a link. Do not extend the
    needle list in place of preserving that. Extend it only to nail a specific
    phrasing that has already shipped.
    """

    def test_no_shipped_document_describes_the_retired_mechanism(self):
        offenders = []
        for relative, text in shipped_documents():
            for claim in RETIRED_MECHANISM_CLAIMS:
                for number, line in offending_lines(text, claim):
                    offenders.append(f"{relative}:{number} ({claim!r}): {line}")
        self.assertEqual(
            offenders,
            [],
            "these lines describe how a no-diff task was recorded before it was "
            "committed empty; see references/state-schema.md:\n" + "\n".join(offenders),
        )

    def test_every_documented_mention_of_no_diff_tasks_is_marked_legacy(self):
        offenders = []
        for relative, text in markdown_documents():
            for number, line in unmarked_legacy_mentions(text):
                offenders.append(f"{relative}:{number}: {line}")
        self.assertEqual(
            offenders,
            [],
            "these lines name `no_diff_tasks` without saying it is legacy, so a "
            "reader takes it for the live mechanism:\n" + "\n".join(offenders),
        )

    def test_the_mechanism_scan_reaches_the_documents_that_described_it(self):
        scanned = [relative for relative, _ in shipped_documents()]
        for expected in (
            ".gitignore",
            "references/phase-transitions.md",
            "references/state-schema.md",
            "scripts/test_int_end_to_end.py",
            "scripts/test_unit_detect_phase.py",
        ):
            self.assertIn(expected, scanned)
        self.assertNotIn(SCANNER, scanned)


class TheCheckItselfDiscriminates(unittest.TestCase):
    """A parity check that cannot fail is worse than no check at all."""

    def test_a_missing_reason_is_named_in_the_failure(self):
        stale = [r for r in update_loop.HALT_REASONS if r != "verify_exhausted"]
        with self.assertRaises(AssertionError) as ctx:
            assert_parity("SKILL.md", stale)
        self.assertIn("verify_exhausted", str(ctx.exception))
        self.assertNotIn("no_progress", str(ctx.exception))

    def test_an_invented_reason_is_named_in_the_failure(self):
        invented = list(update_loop.HALT_REASONS) + ["cosmic_rays"]
        with self.assertRaises(AssertionError) as ctx:
            assert_parity("SKILL.md", invented)
        self.assertIn("cosmic_rays", str(ctx.exception))

    def test_a_vanished_enumeration_names_the_document(self):
        with self.assertRaises(AssertionError) as ctx:
            documented_reasons("SKILL.md", "Reasons we never wrote down:")
        self.assertIn("SKILL.md", str(ctx.exception))

    def test_a_reintroduced_mechanism_description_is_named_with_its_location(self):
        # Verbatim the sentence `references/phase-transitions.md` shipped for a
        # whole verification round after the mechanism changed under it.
        planted = (
            "It is the one piece of completion state git cannot express: a\n"
            "config-only task that legitimately produced no commit, and\n"
            "therefore no trailer.\n"
        )
        offenders = sorted(
            (number, claim)
            for claim in RETIRED_MECHANISM_CLAIMS
            for number, _ in offending_lines(planted, claim)
        )
        self.assertEqual(offenders, [(2, "produced no commit"),
                                     (3, "therefore no trailer")])

    def test_an_unmarked_mention_is_caught_and_a_marked_one_is_not(self):
        unmarked = "The union with `no_diff_tasks` is how a batch closes.\n"
        marked = (
            "The union with `no_diff_tasks` is how a batch closes.\n"
            "\n"
            "That field is legacy: nothing writes it any more.\n"
        )

        self.assertEqual(unmarked_legacy_mentions(unmarked), [(1, unmarked.strip())])
        self.assertEqual(unmarked_legacy_mentions(marked), [])

    def test_a_mention_inside_a_code_fence_is_not_a_claim(self):
        example = '```json\n{\n  "no_diff_tasks": ["T4"]\n}\n```\n'

        self.assertEqual(unmarked_legacy_mentions(example), [])


if __name__ == "__main__":
    unittest.main()
