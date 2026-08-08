"""Resolve this skill's own directory and its sibling `tlc-spec-driven`.

Both skills are installed side by side under one skills directory and are then
symlinked into the harness' own skill directory. Every lookup therefore
resolves symlinks first (`os.path.realpath`) and only then walks to the
sibling, otherwise the sibling is invisible when the skill is reached through
its symlink.

Imported, never invoked directly.
"""

import os

TLC_SKILL_NAME = "tlc-spec-driven"


class SiblingSkillError(RuntimeError):
    """The sibling skill, or one of its scripts, is not where it must be.

    Carries the attempted absolute path so the failure is actionable instead of
    a bare FileNotFoundError with no context.
    """


def skill_dir():
    """Absolute, symlink-resolved directory of the skill that ships this file."""
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def tlc_dir():
    """Absolute path of the sibling `tlc-spec-driven` skill directory."""
    here = skill_dir()
    path = os.path.join(os.path.dirname(here), TLC_SKILL_NAME)
    if not os.path.isdir(path):
        raise SiblingSkillError(
            f"sibling skill {TLC_SKILL_NAME!r} not found at {path} "
            f"(resolved from {here}); install it next to this skill"
        )
    return path


def tlc_script(name):
    """Absolute path of a named script under the sibling skill's `scripts/`."""
    path = os.path.join(tlc_dir(), "scripts", name)
    if not os.path.isfile(path):
        raise SiblingSkillError(
            f"script {name!r} not found at {path}; the sibling skill "
            f"{TLC_SKILL_NAME!r} does not ship it"
        )
    return path
