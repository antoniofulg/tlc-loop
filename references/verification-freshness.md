# Verification freshness

**This file is the skill's only full description of when a verdict still
describes the tree.** Every other mention links here instead of restating it.
That rule is not stylistic: the same claim shipped false four times in this
repository when it lived in four documents, and
[state-schema.md](state-schema.md#the-no-diff-contract) carries the scar from
the last time. One description cannot disagree with itself.

---

## The property

The done-signature means one thing:

> an independent verifier passed the tree that is checked out right now.

`validate_state.py` from the sibling skill answers half of that - the report
says PASS and cites `file:line` evidence. It cannot answer the other half,
because a report is a file and a file says nothing about which commit it was
written against.

So the verdict is recorded together with the commit it covered:
`verify.verified_at`, stamped by `update_loop.py --verify-round`. A verdict
**covers HEAD** when either

1. `HEAD == verified_at`, or
2. HEAD is a valid **seal** over `verified_at`.

There is no third way, and nothing else in the file can substitute for it.
`status = complete` does not. A green gate does not. A passing test suite does
not. Anything committed after the verifier looked is code no verifier has seen,
however small the diff and however green the gates.

An absent `verified_at` counts as uncovered. That is the state a rebuilt
`loop.json` is in: it costs one verify round, which is the cheap side of the
trade.

The predicate is `_gitio.verification_covers_head`, and it is one function on
purpose. `detect_phase.py`, `update_loop.py`, `checkpoint.py` and
`finish_loop.py` all ask it. Four implementations would be four chances to
disagree.

---

## The seal

A verifier reads the tree at commit `V` and writes `validation.md`. Committing
that report moves HEAD past `V` - and a moved HEAD is uncovered. The evidence
could therefore never be versioned without invalidating the thing it is
evidence of.

The **seal** is the one commit that resolves this, and it is deliberately narrow
enough to check:

```bash
python3 <skill-dir>/scripts/checkpoint.py <feature> --root <root> --seal
```

| It must | Because |
| --- | --- |
| be created only at `phase=E` | E is what proves the report is a filled PASS with evidence: `detect_phase.py` reaches it only after `validate_state.py` exits 0. A FAIL, an empty file, or a prose-only report can never get this far, so the phase gate *is* the report gate. |
| have `verified_at` as its only parent | A seal certifies one tree. A chain of seals would let any number of commits ride behind one verdict. |
| change exactly `.specs/features/<feature>/validation.md` | The exception is the evidence. Anything else riding along is a change nobody verified. |
| carry `Verification-Of: <V>` and `Verification-Result: PASS` | So a reader of the history can tell a seal from an ordinary documentation commit. |
| carry no `Task:` trailer | A `Task:` trailer means "a gate passed for a planned task". Inventing one to get the report committed is what produced the incident's post-verification commits. |

It composes its own message and runs it past `check_commit.py` like every other
commit. The caller supplies nothing, so two seals of the same verdict are the
same commit.

The detector **re-derives all four facts** from git rather than believing the
trailers. A trailer is a claim; the point of the seal is that it is the one
post-verification commit small enough to verify independently.

### What the seal refuses

Runtime code, configuration, tests, `tasks.md`, `design.md`, any extra file
staged or unstaged, a second seal on top of a seal, and a verdict that no longer
covers HEAD.

**`tasks.md` and `design.md` are on that list on purpose.** Marking the plan and
updating a design's status are ordinary work: they belong before the final
verification, in the commit whose gate earned them. `checkpoint.py` ticks a
task's header in the same commit as its gate for exactly this reason. A plan
update after the verifier has passed is a change the verifier did not see, and
widening the seal to admit "just documentation" is how the exception stops being
checkable.

---

## Epochs

`verify.max_rounds` bounds a **verification epoch**, not the life of the run.

| Field | Meaning |
| --- | --- |
| `verify.rounds` | Every verify round this run has ever recorded. |
| `verify.epoch_rounds` | Rounds recorded in the current epoch. What `max_rounds` compares against. |

An epoch is the sequence of rounds against one lineage:

- A **PASS closes** it.
- A **non-seal commit landing after that PASS opens the next one**, which starts
  with a full budget.
- A **FAIL does not.** FAIL, fix, re-verify is precisely the non-converging
  cycle the ceiling exists to stop, so it keeps spending from the budget however
  many commits the fixes take.

There is no separate "consecutive failures" counter, because within an epoch
there is nothing else to count: a PASS ends the epoch, so every round the
current one holds was a failure.

The detector does not need a write to notice a new epoch. `last_verdict` is
`PASS` and the verdict does not cover HEAD is the whole condition, and both
halves are already in front of it. `update_loop.py --verify-round` evaluates the
same condition and resets `epoch_rounds` to 1.

**Reading a state written before epochs existed:** `epoch_rounds` absent is read
as `rounds`. That is the conservative migration - an in-flight run keeps exactly
the budget it already had, rather than silently gaining a fresh one - and it is
deterministic and read-side only. Nothing is written back until a real mutation
does it.

The global limits are untouched by any of this. `max_iterations`, `max_minutes`
and `no_progress_iterations` are properties of the run, not of an epoch, and a
reopened epoch spends from the same clock as the first one.

---

## Finishing

`finish_loop.py` is **the only thing in this skill that prints the
done-signature.** No other script contains the string, and a test enforces that.
A goal evaluator or `loop.sh` matching the line is therefore matching this
script's decision rather than a model's summary.

```bash
python3 <skill-dir>/scripts/finish_loop.py <feature> --root <root>
```

It re-derives every fact rather than being told any of them:

1. `detect_phase.py` prints exactly `phase=E action=done`.
2. The working tree carries no change, except `loop.json`, which is machine
   state and belongs in `.gitignore`.
3. The verdict covers HEAD.
4. Completion is recorded through `update_loop.py`, the single writer.
5. HEAD has not moved since step 1, and 1 to 3 hold again.
6. The signature is printed, as the last line.

Step 5 is not the script distrusting itself. Checking once and then acting is a
race with everything else on the machine, and the window it closes has the same
shape as the incident: something committed while the run believed it was
finished.

`update_loop.py --status complete` carries the narrower half of the same guard -
a PASS that covers HEAD - so the field cannot outlive its evidence even when the
flag is typed by hand.

---

## Committing after a PASS

`checkpoint.py` refuses an ordinary task commit whenever the detector reports
`phase=E` or `phase=H`. A finished or halted run has nothing left to record, and
a commit landing there is unverified code by construction.

Two named routes exist instead, and neither is a way around the rule:

| Route | For | Effect |
| --- | --- | --- |
| `--seal` | the validation report | Keeps coverage. See above. |
| `--reopen` | a change that must land anyway | **Destroys** coverage, deliberately. |

`--reopen` is the route for a base branch that moved under a finished feature:

```bash
git merge --no-commit --no-ff origin/main     # resolve conflicts, run the gates
python3 <skill-dir>/scripts/checkpoint.py <feature> --root <root> --reopen \
  --message "chore(<feature>): integrate the base branch"
```

It commits through the authorized writer, carries
`Reopens-Verification: <the verdict it invalidates>`, and no `Task:` trailer.
It writes no state: git moving *is* the invalidation. The next detect finds a
PASS that no longer covers HEAD, opens a fresh epoch, and asks for a fresh
independent verification of the merged tree. Passing the gates again is not a
substitute - the gates ran before the merge too.

`--no-commit` leaves `MERGE_HEAD` in place, so the commit `--reopen` creates is
a real merge commit with both parents.

---

## Before publishing

Push and PR creation stay outside this skill and outside its authorization; see
the blast-radius rule in [SKILL.md](../SKILL.md). What the skill can answer,
read-only, is whether HEAD is safe to publish at all:

```bash
python3 <skill-dir>/scripts/finish_loop.py <feature> --root <root> \
  --preflight origin/main
```

Every check above, plus one: the base ref must already be an ancestor of HEAD.
A base that has moved ahead means a push or PR would drag a merge nobody
verified behind it, so the preflight refuses and names the way out - integrate
the base, re-run the gates, take a fresh independent verification, seal it,
finish.

It writes nothing and never prints the signature.
