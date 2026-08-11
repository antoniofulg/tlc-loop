# Parity Guards Prove Intent Specification

## Problem Statement

The four docs-parity guards that assert a required command match a substring
anywhere inside their scope. They therefore prove the command is *present*, not
that the document *instructs the reader to run it*. The `halt-resume` verifier
demonstrated three ways a document can be wrong while its guard stays green,
and one way a correct document fails.

Recorded in `.specs/features/halt-resume/validation.md:159-162`:

| Probe | Mutation | Result |
| --- | --- | --- |
| P1 | The Phase H command left in place, prefixed "Never run this, it is not a supported operation" | survived |
| P1b | The real instruction replaced by "A human deletes `loop.json` and starts over. Whatever you do, never run:" plus the same block | survived - intent inverted, guard green |
| P2 | The `` ## `halt` `` block wrapped in an HTML comment | survived - commented-out text counts as documentation |
| P7 | A column-0 `#` inside a fenced block in Phase H | killed a *harmless* edit - `section()` reads it as a heading and truncates the scope |

P1b is the worst of the four: the document tells the reader to do the exact
thing the feature exists to prevent, and the suite reports PASS.

## Goals

- [ ] A command inside an HTML comment, or present only in prose, no longer satisfies a guard that asserts an instruction.
- [ ] A fenced command introduced by a negated imperative fails its guard, naming the marker.
- [ ] A `#` inside a fenced block no longer truncates a section scope.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| The prose scans (`RETRACTED_CLAIMS`, `RETIRED_MECHANISM_CLAIMS`, `StageRoutingContractParity`) | They assert phrases, not commands, and none was breached. Extending comment-blindness to them touches checks that currently pass, for a false-positive risk nobody has hit. |
| Parsing Markdown with a library | The file has no dependencies and `_fenced()` already does line-based fence tracking. A parser is more machinery than four guards earn. |
| Proving intent in general | Out of reach for a substring check. The target is the three failure modes that shipped, not every way prose can lie. |
| Natural-language negation detection | A fixed vocabulary of negated imperatives, verified against this corpus. See the assumption below. |
| Changing any shipped document | No prose is wrong today. This is guard precision only. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| How negation is detected | A fixed vocabulary of negated imperatives (`never run`, `do not call`, `don't use`, ...), matched against the last clause before the fence | The user chose an explicit vocabulary. Verified against the shipped corpus: 0 false positives, and it flags both P1 and P1b. | y |
| Vocabulary is verb-specific, not bare negation words | Yes | Measured, not assumed. `rather than` introduces 3 fences affirmatively, and `SKILL.md:237` introduces a correct `--halt executor` instruction with "do not retry - a timeout is an executor failure, not a flake:". A bare-word list would fail 4 valid documents on day one. | y |
| Residual risk of the vocabulary | Accepted and recorded | A negation phrased outside the list ("this call was removed in 0.4:") still passes. The guard narrows the hole; it does not close it. Stated in the test docstring so the next reader is not misled. | y |
| Scope of the negation scan | The last clause before the fence, split on `". "` | A 3-line window flags `SKILL.md:237`, which is a correct instruction. The clause that ends in the colon is the one that introduces the command. | y |
| Which guards get the fence requirement | The three whose artifact is a fenced block | The `H` transition row is an inline mention inside a table cell (`references/phase-transitions.md:252`), so requiring a fence there would fail a correct document. It gets comment-stripping and negation only. | y |
| Whether HTML comments are stripped or flagged | Stripped before scanning | A commented-out instruction is not an instruction. Stripping gives the guard the reader's view. `assets/iteration-summary.template.md` uses comments legitimately, so flagging them would be wrong. | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: A guard rejects a document that does not instruct ⭐ MVP

**User Story**: As a maintainer relying on the parity suite, I want a guard to
fail when the command it requires is commented out, prose-only, or negated, so
that a green suite means the instruction is really there.

**Why P1**: The suite's whole value is that it fails when the docs drift. Three
demonstrated drifts leave it green, and one of them inverts the instruction.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN a guard scans a document THEN it SHALL ignore every `<!-- ... -->` span, including spans covering more than one line.
2. IF the only occurrence of a required command lies inside an HTML comment THEN the guard SHALL fail, naming the document.
3. WHILE a guard asserts a command whose artifact is a fenced block, WHEN the command appears only in prose outside any fence THEN the guard SHALL fail, naming the document.
4. IF the last clause before a required command's fence contains a negated imperative from the recorded vocabulary THEN the guard SHALL fail, naming the marker it matched.
5. WHEN the negation scan reads the prose introducing a fence THEN it SHALL consider only the clause after the final `". "`, so an earlier sentence's wording cannot flag a correct instruction.
6. The negation vocabulary SHALL contain only verb-specific negated imperatives, and SHALL flag none of the fences in the shipped documents.
7. WHERE a guard asserts an inline mention rather than a fenced block, it SHALL apply criteria 1, 2 and 4 and SHALL NOT require a fence.

**Independent Test**: Wrap the Phase H command block in an HTML comment and
confirm the suite fails naming `SKILL.md`; repeat with the block moved to prose,
and with "never run:" introducing it.

---

### P2: A fenced `#` does not truncate a scope

**User Story**: As an author editing the shipped docs, I want a `#` inside a
code block to stay code, so that adding a shell comment to an example does not
fail a guard about a different section.

**Why P2**: The opposite failure to P1 and cheaper to hit. A contributor adding
`# resolve the cause first` to a bash example silently shrinks the scope of a
guard that has nothing to do with their edit.

**Acceptance Criteria**:

1. WHEN the section scan looks for the heading that ends a section THEN it SHALL ignore lines inside fenced code blocks.
2. WHEN a fenced block inside a section contains a line starting with `#` THEN the returned section SHALL still extend to the next real heading.
3. IF a section's fenced block contains a line starting with `#` THEN the guards asserting inside that section SHALL still pass on the shipped documents.

**Independent Test**: Insert `# a comment` at column 0 inside the Phase H bash
block and confirm the Phase H guard still passes and still stops at `### Step 3`.

---

## Edge Cases

- WHEN an HTML comment opens and never closes THEN the scan SHALL treat the remainder of the document as commented, so an unterminated comment cannot hide text by accident.
- WHEN a required command appears both inside a comment and in a live fenced block THEN the guard SHALL pass, because the live instruction exists.
- IF a document contains no fenced block at all THEN a guard requiring a fenced command SHALL fail rather than raise, and the failure SHALL name the document.
- WHEN a fence is introduced by a clause containing a negated imperative *and* the same section carries a second, affirmative instance of the command THEN the guard SHALL pass, because a supported route is documented.
- WHEN the negation vocabulary is checked against every fence in the shipped documents THEN it SHALL match none, and a test SHALL assert this so a later addition to the vocabulary cannot silently break valid prose.

---

## Requirement Traceability

| Requirement ID | Story | Covers | Phase | Status |
| -------------- | ----- | ------ | ----- | ------ |
| INTENT-01 | P1: A guard rejects a document that does not instruct | P1 AC 1, 2 - HTML comments are invisible to every command guard | T1 | Implementing |
| INTENT-02 | P1: A guard rejects a document that does not instruct | P1 AC 3, 7 - a fenced-artifact guard requires a fence; an inline guard does not | Tasks | Pending |
| INTENT-03 | P1: A guard rejects a document that does not instruct | P1 AC 4, 5, 6 - the negated-imperative vocabulary and the clause it reads | Tasks | Pending |
| INTENT-04 | P2: A fenced `#` does not truncate a scope | P2 AC 1, 2, 3 - the section scan skips fenced lines | T2 | Implementing |

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 4 total, 0 mapped to tasks, 4 unmapped ⚠️

---

## Success Criteria

- [ ] Re-running the verifier's P1, P1b and P2 probes kills all three.
- [ ] Re-running the P7 probe no longer fails a harmless edit.
- [ ] `python3 -m unittest discover -s scripts -p 'test_*.py'` passes with no shipped document changed.
- [ ] The negation vocabulary matches no fence in any shipped document, asserted by a test.
