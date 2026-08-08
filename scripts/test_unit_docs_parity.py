"""Parity between the shipped prose and the code it describes (T33, LOOP-06).

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

#: Where each document enumerates the vocabulary, and the phrase that anchors
#: it. The enumeration runs from the anchor to the end of that sentence.
ENUMERATIONS = (
    ("SKILL.md", "Implemented reasons:"),
    ("references/phase-transitions.md", "`reason=<slug>` is one of"),
)

BACKTICKED = re.compile(r"`([a-z_]+)`")


def documented_reasons(relative_path, anchor):
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
    end = sentence.find(".\n")
    if end < 0:
        raise AssertionError(
            f"{relative_path}: the enumeration after {anchor!r} does not end "
            "in a sentence; parity can no longer be checked"
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

    def test_every_documented_enumeration_is_locatable(self):
        for relative_path, anchor in ENUMERATIONS:
            with self.subTest(document=relative_path):
                self.assertTrue(documented_reasons(relative_path, anchor))


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
