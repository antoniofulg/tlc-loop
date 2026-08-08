"""Parity between the shipped prose and the code it describes (T33, LOOP-06).

Two checks live here. The first is the halt vocabulary; the second (T38) is the
claim about what deleting `loop.json` costs, which drifted through three
verification rounds because each fix chased the citations it was handed instead
of searching the repository.

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
import unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

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

#: The surface an agent actually reads at runtime, plus the source that
#: describes itself. Deliberately excludes `.specs/`: `validation.md` quotes the
#: false claims as findings, `tasks.md` quotes them as criteria, and
#: `LESSONS.md` quotes them as the lesson.
def shipped_documents():
    """Every shipped document and non-test script, as `(relative_path, text)`."""
    found = []
    for relative in ("SKILL.md", "README.md"):
        found.append(relative)
    for directory in ("references", "assets", "scripts"):
        for name in sorted(os.listdir(os.path.join(ROOT, directory))):
            if name.startswith("test_"):
                continue
            if name.endswith((".md", ".py", ".sh", ".toml")):
                found.append(f"{directory}/{name}")
    for relative in found:
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


if __name__ == "__main__":
    unittest.main()
