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

- [x] A command inside an HTML comment, or present only in prose, no longer satisfies a guard that asserts an instruction.
- [x] A fenced command introduced by a negated imperative fails its guard, naming the marker.
- [x] A `#` inside a fenced block no longer truncates a section scope.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| The prose scans (`RETRACTED_CLAIMS`, `RETIRED_MECHANISM_CLAIMS`, `StageRoutingContractParity`) | They assert phrases, not commands, and none was breached. Extending comment-blindness to them touches checks that currently pass, for a false-positive risk nobody has hit. |
| Parsing Markdown with a library | The file has no dependencies and `_fenced()` already does line-based fence tracking. A parser is more machinery than four guards earn. |
| Proving intent in general | Out of reach for a substring check. The target is the three failure modes that shipped, not every way prose can lie. |
| Natural-language negation detection | A fixed vocabulary of negated imperatives, verified against this corpus. See the assumption below. |
| Changing any shipped document | No prose is wrong today. This is guard precision only. |
| An unterminated-fence rule in `_fenced()` | `fence_spans()` treats an unclosed fence as running to the end and a test pins that. `_fenced()` is left alone: it serves the `no_diff_tasks` scan, 0 shipped documents have an odd fence count, and changing it would touch a check this feature has no quarrel with. **Recorded, not fixed.** |
| `visible()` stripping `<!--` inside a code fence | A fenced example containing `<!--` would be partly erased before scanning, turning a valid document red - the same false-positive class as P7. 0 shipped fences contain it, and making `visible()` fence-aware means splitting lines before comments are removed, which inverts the order the other helpers assume. **Recorded, not fixed.** |
| `fenced_commands()` concatenating abutting fences | Two blocks separated by nothing are joined, so a command split across them would read as one. 0 shipped documents have abutting fences, and the join is what lets a wrapped call match at all. **Recorded, not fixed.** |
| An upper bound on `INTRO_LINES` | The lower bound is pinned - a wrapped introducing sentence must still be read - and widening past 4 is caught by the corpus safety net rather than by a boundary test. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| How negation is detected | A fixed vocabulary of negated imperatives (`never run`, `do not call`, `don't use`, ...), matched against the last clause before the fence | The user chose an explicit vocabulary. Verified against the shipped corpus: 0 false positives, and it flags both P1 and P1b. | y |
| Vocabulary is verb-specific, not bare negation words | Yes | Measured, not assumed. `rather than` introduces 3 fences affirmatively, and `SKILL.md:237` reaches a correct `--halt executor` instruction through "do not retry - a timeout is an executor failure, not a flake:". A bare-word list would fail valid documents on day one, and `test_a_bare_negation_list_would_flag_shipped_prose` keeps that measurement executable. This vocabulary is the *only* thing preventing those false positives; the lookbehind window does not help with it. | y |
| Residual risk of the vocabulary | Accepted and recorded | A negation phrased outside the list ("this call was removed in 0.4:") still passes. The guard narrows the hole; it does not close it. Stated in the test docstring so the next reader is not misled. | y |
| Scope of the negation scan | The `INTRO_LINES` lines above the command's own fence opener, or the same-line text before an inline mention | **Corrected after verification.** The original rationale - that a line window flags `SKILL.md:237` - was false: that line says "do not retry", and `retry` is not an imperative verb in the vocabulary, so no window could ever flag it. The clause split protected nothing and its test could not fail. What the anchor actually fixes is real: anchored to the scan instead of the command, a negation directly above a one-line command fell outside its own lookbehind. | y |
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
5. WHEN the negation scan reads the prose introducing a command THEN it SHALL anchor the lookbehind to that command's own fence opener, or to the text preceding it on its own line where the criterion names an inline mention.
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
- WHILE a guard names a fenced artifact, WHEN an affirmative mention of the command appears in prose outside any fence THEN it SHALL NOT rescue a fenced occurrence its own prose negates.
- WHEN a negated imperative introduces a command from up to `INTRO_LINES` lines above its fence THEN the scan SHALL still read it, so a wrapped introducing sentence is not missed.
- IF a criterion names an inline mention THEN the negation SHALL be read from the text before the command on the same line, because a table row has no lines above it to read.

---

## Requirement Traceability

| Requirement ID | Story | Covers | Phase | Status |
| -------------- | ----- | ------ | ----- | ------ |
| INTENT-01 | P1: A guard rejects a document that does not instruct | P1 AC 1, 2 - HTML comments are invisible to every command guard | T1 | Verified |
| INTENT-02 | P1: A guard rejects a document that does not instruct | P1 AC 3, 7 - a fenced-artifact guard requires a fence; an inline guard does not | T3 | Verified |
| INTENT-03 | P1: A guard rejects a document that does not instruct | P1 AC 4, 5, 6 - the negated-imperative vocabulary and the clause it reads | T4 | Verified |
| INTENT-04 | P2: A fenced `#` does not truncate a scope | P2 AC 1, 2, 3 - the section scan skips fenced lines | T2 | Verified |

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 4 total, 4 mapped to tasks, 0 unmapped

---

## Success Criteria

- [x] Re-running the verifier's P1, P1b and P2 probes kills all three.
- [x] Re-running the P7 probe no longer fails a harmless edit.
- [x] `python3 -m unittest discover -s scripts -p 'test_*.py'` passes with no shipped document changed.
- [x] The negation vocabulary matches no fence in any shipped document, asserted by a test.
