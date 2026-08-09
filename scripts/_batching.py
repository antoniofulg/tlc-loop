"""Pack phases into task-budgeted batches.

A **phase** is the semantic unit authored during Tasks and is indivisible. A
**batch** is the execution unit: one or more *consecutive whole phases* packed
to roughly the task budget. The cut only ever lands on a phase boundary, which
is what keeps dependency ordering and a phase's shared context intact.

The algorithm is the one in `tlc-spec-driven/references/sub-agents.md`: walk
phases in order, accumulate whole phases, close the batch once it has reached
the budget, and fold a lone tail of one or two tasks back into the previous
batch.

One guard is added on top, taken from that document's own coarse-phase
threshold: a non-empty batch does not accept a phase that would push it past
1.5x the budget. Without it, `[8, 2, 2, 8]` collapses into two batches, since
the running count sits below the budget right up to a final oversized append.

A phase that alone exceeds 1.5x the budget is a Tasks-authoring smell. It is
reported to the caller and still emitted whole: splitting it here would undo
the decision the Tasks phase made.

Imported, never invoked directly.
"""

COARSE_FACTOR = 1.5


def _group_by_phase(tasks):
    """Ordered phase groups with task ids and one effective stage each."""
    grouped = {}
    for task in tasks:
        phase = task["phase"]
        stage = task.get("effective_stage") or "implement"
        group = grouped.setdefault(phase, {"tasks": [], "stage": stage})
        if group["stage"] != stage:
            raise ValueError(
                f"phase {phase} mixes effective stages {group['stage']!r} and {stage!r}"
            )
        group["tasks"].append(task["id"])
    return grouped


def pack(tasks, budget=7):
    """Return `(batches, oversized_phases)`.

    Each batch is `{"phases": [...], "tasks": [...], "stage": name}` holding
    consecutive whole phases with one effective stage. `oversized_phases` lists
    phases larger than 1.5x the budget, which are flagged rather than split.
    """
    grouped = _group_by_phase(tasks)
    cap = COARSE_FACTOR * budget
    oversized = [
        phase for phase, group in grouped.items() if len(group["tasks"]) > cap
    ]

    batches = []
    current = None
    for phase, group in grouped.items():
        ids, stage = group["tasks"], group["stage"]
        if current is not None and (
            current["stage"] != stage
            or len(current["tasks"]) >= budget
            or len(current["tasks"]) + len(ids) > cap
        ):
            batches.append(current)
            current = None
        if current is None:
            current = {"phases": [], "tasks": [], "stage": stage}
        current["phases"].append(phase)
        current["tasks"] += ids
    if current is not None:
        batches.append(current)

    # A lone tail of one or two tasks is not worth its own worker.
    if (
        len(batches) > 1
        and len(batches[-1]["tasks"]) <= 2
        and batches[-1]["stage"] == batches[-2]["stage"]
    ):
        tail = batches.pop()
        batches[-1]["phases"] += tail["phases"]
        batches[-1]["tasks"] += tail["tasks"]

    return batches, oversized
