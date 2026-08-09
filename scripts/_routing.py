"""Resolve declared phase Stages to effective implementation stages.

This module owns fallback and Phase-B reservations. Provider/model resolution
stays in `resolve_stage.py`; batching receives only validated effective stages.
"""

import re


STAGE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
RESERVED_STAGES = frozenset(("verify", "fix", "continue.respawn"))


class RoutingError(Exception):
    """One or more phases cannot be routed safely."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def resolve(phases, config):
    """Return copied phase records annotated with `effective_stage`.

    A missing declaration falls back to `implement` only when routing is not
    strict. An explicit typo, malformed name, reserved runtime role, or missing
    config entry is always an error. All phase errors are reported together.
    """
    strict = config["execute"]["strict_routing"]
    configured = config["stages"]
    routed = []
    errors = []

    for phase in phases:
        number = phase["number"]
        declared = phase.get("declared_stage")
        effective = None

        if declared is None:
            if strict:
                errors.append(f"Phase {number}: missing Stage while strict_routing is true")
            else:
                effective = "implement"
        elif declared in RESERVED_STAGES:
            errors.append(
                f"Phase {number}: Stage {declared!r} is reserved for a runtime role"
            )
        elif not STAGE_NAME_RE.fullmatch(declared):
            errors.append(
                f"Phase {number}: Stage {declared!r} must use lowercase kebab-case"
            )
        elif declared not in configured:
            errors.append(
                f"Phase {number}: Stage {declared!r} is not configured under [stages.{declared}]"
            )
        else:
            effective = declared

        record = dict(phase)
        record["tasks"] = list(phase.get("tasks") or [])
        record["effective_stage"] = effective
        routed.append(record)

    if errors:
        raise RoutingError(errors)
    return routed
