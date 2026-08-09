"""Reader for `.specs/loop.config.toml` - user-owned, read-only to the loop.

TOML via stdlib `tomllib`, so there is no dependency and no hand-written
parser. TOML has no `null`, so an omitted key under `[limits]` means
*unlimited* (D8); unlimited is represented as `None` in the returned config.
`verify.max_rounds` follows the same rule: the verify ceiling is configurable
with no hard-coded maximum (D5), so omitting it imposes none.

Every absent key resolves to its documented default, which is why an absent
file is a valid configuration rather than an error. An `effort` the loop knows
no provider accepts is rejected here, at load time, so a bad pairing never
reaches dispatch (LOOP-05 AC 2). A `[limits]` value that is not a positive
integer is rejected for the same reason: a limit the loop cannot compare
against is a limit that never fires, and a ceiling that never fires is
indistinguishable from a hang.

Every key this module defaults has a reader in a non-test script, and
`test_unit_config.py` asserts it. A key that configures nothing is worse than
an absent one: it reads as a promise.

Imported, never invoked directly.
"""

import os
import tomllib

#: Effort values any provider accepts. `ultra` is deliberately absent.
EFFORTS = ("low", "medium", "high", "xhigh", "max")

#: Schema versions this loop understands. Checked at bootstrap by
#: `init_loop.py`, so a config written for a different schema is refused
#: before a run starts rather than half-honoured hours in.
SUPPORTED_VERSIONS = (1,)

#: Values `continue.mode` accepts, from the continuation table in `SKILL.md`.
#: Checked at bootstrap: a typo here silently picks the wrong way to restart a
#: turn, which is the failure nobody sees until morning.
CONTINUE_MODES = ("auto", "goal", "shell", "none")

_STAGE_DEFAULT = {"provider": "auto", "model": None, "effort": None}

#: Keys under `[limits]`. All default to None, which means unlimited (D8).
LIMIT_KEYS = (
    "no_progress_iterations",
    "gate_attempts_per_task",
    "executor_timeout_seconds",
    "max_iterations",
    "max_minutes",
)


class ConfigError(Exception):
    """`loop.config.toml` does not parse, or configures a value the loop rejects."""


def config_path(root):
    """Absolute path of the config file for a project root."""
    return os.path.join(os.path.abspath(root), ".specs", "loop.config.toml")


def defaults():
    """The fully-defaulted config, as used when the file is absent."""
    return {
        "version": 1,
        "stages": {
            "implement": dict(_STAGE_DEFAULT),
            "verify": dict(_STAGE_DEFAULT),
            "fix": dict(_STAGE_DEFAULT),
        },
        "execute": {"batch_size": 7},
        # No hard-coded maximum (D5): the ceiling exists only when the user
        # sets one, exactly like a `[limits]` key.
        "verify": {"max_rounds": None},
        "continue": {"mode": "auto", "respawn": dict(_STAGE_DEFAULT)},
        "limits": {key: None for key in LIMIT_KEYS},
        "providers": {},
    }


def _merge_stage(base, raw):
    stage = dict(base)
    for key in ("provider", "model", "effort"):
        if key in raw:
            stage[key] = raw[key]
    return stage


def _check_effort(cfg):
    named = [(f"stages.{name}", stage) for name, stage in sorted(cfg["stages"].items())]
    named.append(("continue.respawn", cfg["continue"]["respawn"]))
    for label, stage in named:
        effort = stage.get("effort")
        if effort is None:
            continue
        if effort not in EFFORTS:
            raise ConfigError(
                f"{label}: unknown effort {effort!r}; accepted values are "
                f"{', '.join(EFFORTS)}"
            )


def _check_limits(cfg):
    """Every `[limits]` value is a positive integer, or the key is absent.

    `0` is rejected rather than read as "unlimited": omission already means
    unlimited (D8), so a zero is a typo, and a ceiling of zero would halt the
    run on its first iteration.
    """
    for key in LIMIT_KEYS:
        value = cfg["limits"][key]
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ConfigError(
                f"limits.{key}: expected a positive integer, got {value!r}; "
                f"omit the key entirely to mean unlimited"
            )


def load_config(root):
    """Return the config for a project root, with every absent key defaulted."""
    cfg = defaults()
    path = config_path(root)
    if not os.path.isfile(path):
        return cfg

    try:
        with open(path, "rb") as fh:
            raw = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: malformed TOML: {exc}") from exc

    if "version" in raw:
        cfg["version"] = raw["version"]
    for name, stage in (raw.get("stages") or {}).items():
        cfg["stages"][name] = _merge_stage(cfg["stages"].get(name, _STAGE_DEFAULT), stage)
    if "batch_size" in (raw.get("execute") or {}):
        cfg["execute"]["batch_size"] = raw["execute"]["batch_size"]
    if "max_rounds" in (raw.get("verify") or {}):
        cfg["verify"]["max_rounds"] = raw["verify"]["max_rounds"]

    cont = raw.get("continue") or {}
    if "mode" in cont:
        cfg["continue"]["mode"] = cont["mode"]
    cfg["continue"]["respawn"] = _merge_stage(
        cfg["continue"]["respawn"], cont.get("respawn") or {}
    )

    for key in LIMIT_KEYS:
        if key in (raw.get("limits") or {}):
            cfg["limits"][key] = raw["limits"][key]

    cfg["providers"] = raw.get("providers") or {}

    _check_effort(cfg)
    _check_limits(cfg)
    return cfg
