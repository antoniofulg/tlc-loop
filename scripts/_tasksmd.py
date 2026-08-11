"""Read the plan out of a feature's `tasks.md`.

`tasks.md` is read-only to the loop: it supplies task ids, their phase, and the
`Depends on` / `Tests` / `Gate` fields. Task *status* never comes from here, it
comes from git trailers.

One field is status-shaped and is deliberately not status: `done` is the human
tick (`✅`) on a task's own header. It is a *claim* that the task is finished,
not the answer to whether it is. `tasks.md` has no status field, so a tick and
git can disagree; git wins and the override is recorded rather than applied
silently (LOOP-01 AC 5). A header with no tick makes no claim either way, which
is why only a ticked-but-uncommitted task is a contradiction.

Field patterns follow the ones `tlc-spec-driven/scripts/validate_tasks.py`
already accepts, so a file that validates there parses here, bold markers and
all.

**Phase membership** is taken from a task id's first appearance inside a
`### Phase N` section, counting both the diagram fences and task headers. A
task's own `### TN:` header is not a reliable anchor on its own: the standard
template declares every phase with a diagram in the Execution Plan and then
defines all tasks in a single flat Task Breakdown afterwards, which would put
every task in the last phase. Both layouts resolve correctly this way.

Imported, never invoked directly.
"""

import re

TASK_RE = re.compile(r"^#{2,4}\s+(T\d+)\s*:", re.IGNORECASE)
PHASE_PREFIX_RE = re.compile(r"^#{2,4}\s+Phase\b", re.IGNORECASE)
PHASE_RE = re.compile(
    r"^#{2,4}\s+Phase\s+([1-9]\d*)\s*:\s*(\S(?:.*\S)?)\s*$",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
STAGE_RE = re.compile(
    r"^(?:\*{0,2}Stage:\*{0,2}|\*{0,2}Stage\*{0,2}\s*:)\s*(.*?)\s*$",
    re.IGNORECASE,
)
TASK_ID_RE = re.compile(r"\bT\d+\b", re.IGNORECASE)
DEPENDS_RE = re.compile(r"^\*{0,2}Depends on\*{0,2}\s*:\s*(.*)$", re.IGNORECASE)
TESTS_RE = re.compile(r"^\*{0,2}Tests\*{0,2}\s*:\s*(.*)$", re.IGNORECASE)
GATE_RE = re.compile(r"^\*{0,2}Gate\*{0,2}\s*:\s*(.*)$", re.IGNORECASE)
#: The completion tick a human leaves on a finished task's header.
DONE_MARK_RE = re.compile(r"✅\s*$")


class TasksFormatError(Exception):
    """`tasks.md` contains an ambiguous phase or Stage declaration."""


def _phase_definitions(lines):
    """Return ordered phase metadata and reject ambiguous phase declarations."""
    phases = []
    seen_numbers = set()
    current = None
    in_fence = False

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if PHASE_PREFIX_RE.match(stripped):
            match = PHASE_RE.match(stripped)
            if not match:
                raise TasksFormatError(
                    f"line {line_number}: expected an integer phase number and title "
                    f"in `### Phase N: Title`, got {stripped!r}"
                )
            number = int(match.group(1))
            if number in seen_numbers:
                raise TasksFormatError(f"line {line_number}: duplicate Phase {number}")
            seen_numbers.add(number)
            current = {
                "number": number,
                "title": match.group(2),
                "declared_stage": None,
                "tasks": [],
                "_level": len(stripped) - len(stripped.lstrip("#")),
                "_stage_seen": False,
                "_stage_allowed": True,
            }
            phases.append(current)
            continue

        if current is None or not stripped:
            continue

        heading = HEADING_RE.match(stripped)
        task_header = TASK_RE.match(stripped)
        if heading and not task_header and len(heading.group(1)) <= current["_level"]:
            current = None
            continue

        stage = STAGE_RE.match(stripped)
        if stage:
            if current["_stage_seen"]:
                raise TasksFormatError(
                    f"line {line_number}: duplicate Stage for Phase {current['number']}"
                )
            if not current["_stage_allowed"]:
                raise TasksFormatError(
                    f"line {line_number}: Stage must be the first non-empty line "
                    f"after Phase {current['number']}"
                )
            current["declared_stage"] = stage.group(1)
            current["_stage_seen"] = True
            current["_stage_allowed"] = False
            continue

        current["_stage_allowed"] = False

    for phase in phases:
        for private in ("_level", "_stage_seen", "_stage_allowed"):
            phase.pop(private)
    return phases


def _phase_membership(lines):
    """Map task id -> phase number, from the `### Phase N` sections."""
    membership = {}
    phase = None
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        match = PHASE_RE.match(stripped)
        if match and not in_fence:
            phase = int(match.group(1))
            continue
        if phase is None:
            continue
        # Inside a phase section, a task belongs to it if its id shows up in a
        # diagram fence or as a task header. First appearance wins.
        header = TASK_RE.match(stripped)
        found = [header.group(1)] if header else (TASK_ID_RE.findall(stripped) if in_fence else [])
        for raw in found:
            membership.setdefault(raw.upper(), phase)
    return membership


def _unique(ids):
    out = []
    for value in ids:
        if value not in out:
            out.append(value)
    return out


def parse(path):
    """Return the file's tasks, in document order.

    Each entry is a dict with `id`, `phase` (int or None), `depends_on` (list),
    `tests` (str or None), `gate` (str or None) and `done` (bool - the header
    carries the human completion tick). A file with no tasks yields an empty
    list.
    """
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()

    membership = _phase_membership(lines)
    tasks, current = [], None
    for line in lines:
        stripped = line.strip()
        header = TASK_RE.match(stripped)
        if header:
            task_id = header.group(1).upper()
            current = {
                "id": task_id,
                "phase": membership.get(task_id),
                "depends_on": [],
                "tests": None,
                "gate": None,
                "done": bool(DONE_MARK_RE.search(stripped)),
            }
            tasks.append(current)
            continue
        if current is None:
            continue

        depends = DEPENDS_RE.match(stripped)
        if depends:
            body = depends.group(1)
            if "none" not in body.lower():
                current["depends_on"] = _unique(
                    m.upper() for m in TASK_ID_RE.findall(body)
                )
            continue
        tests = TESTS_RE.match(stripped)
        if tests:
            current["tests"] = tests.group(1).strip()
            continue
        gate = GATE_RE.match(stripped)
        if gate:
            current["gate"] = gate.group(1).strip()
    return tasks


def mark_done(path, task_id):
    """Add the completion tick to a task's header. True when the file changed.

    The tick is a *claim*, which is exactly why it is written here: `checkpoint`
    applies it in the same commit as the gate that earned it, so the plan and
    the `Task:` trailer are recorded together and cannot disagree. A tick added
    later is a second commit against a tree a verifier may already have passed.

    A task the plan does not declare, or one already ticked, leaves the file
    byte-identical.
    """
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines(keepends=True)

    wanted = task_id.upper()
    for index, line in enumerate(lines):
        header = TASK_RE.match(line.strip())
        if not header or header.group(1).upper() != wanted:
            continue
        body = line.rstrip("\r\n")
        if DONE_MARK_RE.search(body):
            return False
        lines[index] = body + " ✅" + line[len(body):]
        with open(path, "w", encoding="utf-8") as handle:
            handle.writelines(lines)
        return True
    return False


def parse_phases(path):
    """Return ordered phase records with title, declared Stage, and task ids.

    Phase numbers must be positive integers and unique. `Stage`, when present,
    is the first non-empty line after its phase heading. Task membership follows
    the same diagram-or-nested-header rules as :func:`parse`.
    """
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()

    phases = _phase_definitions(lines)
    membership = _phase_membership(lines)
    by_number = {phase["number"]: phase for phase in phases}
    for task in parse(path):
        phase = by_number.get(membership.get(task["id"]))
        if phase is not None:
            phase["tasks"].append(task["id"])
    return phases
