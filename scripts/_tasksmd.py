"""Read the plan out of a feature's `tasks.md`.

`tasks.md` is read-only to the loop: it supplies task ids, their phase, and the
`Depends on` / `Tests` / `Gate` fields. Task *status* never comes from here, it
comes from git trailers.

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
PHASE_RE = re.compile(r"^#{2,4}\s+Phase\s+(\d+)", re.IGNORECASE)
TASK_ID_RE = re.compile(r"\bT\d+\b", re.IGNORECASE)
DEPENDS_RE = re.compile(r"^\*{0,2}Depends on\*{0,2}\s*:\s*(.*)$", re.IGNORECASE)
TESTS_RE = re.compile(r"^\*{0,2}Tests\*{0,2}\s*:\s*(.*)$", re.IGNORECASE)
GATE_RE = re.compile(r"^\*{0,2}Gate\*{0,2}\s*:\s*(.*)$", re.IGNORECASE)


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
    `tests` (str or None) and `gate` (str or None). A file with no tasks yields
    an empty list.
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
