# Goal condition template

Replace `<FEATURE>` with the feature name everywhere below. Nothing else needs
editing.

## The done-signature

The loop prints this line, and only this line, once `validate_state.py` exits 0:

```
__TLC_LOOP__ feature=<FEATURE> verify=PASS
```

The feature name is part of the signature. Two features running in one
transcript would otherwise satisfy each other's condition.

## Claude Code - `/goal`

Paste as the condition. It is 577 characters once `<FEATURE>` is filled in,
well under the documented 4000-character ceiling for a `/goal` condition:

```
The conversation contains, verbatim, one of these two lines:

  __TLC_LOOP__ feature=<FEATURE> verify=PASS

  phase=H action=halt reason=<slug> detail="<text>"

Judge only on the literal presence of one of those lines for feature
<FEATURE>. Nothing else counts: not a summary saying the feature is
finished, not a green test run, not a passing verification report, not a
statement that all tasks are complete. A `phase=E action=done` line on
its own does not count either - the signature line must be present.

If neither line is in the conversation, the goal is not met.
```

Non-interactive:

```bash
claude -p "/goal <paste the condition here>"
```

### Why the condition anchors on printed output

The evaluator reads the conversation. It does not run commands and does not
read files. It cannot run `validate_state.py`, cannot open `validation.md`, and
cannot check `git log`, so a condition phrased as "`validate_state.py` exits 0"
would never fire, whatever the repository actually looks like.

So the loop moves the verdict into the transcript: the script decides, the loop
prints the decision, the evaluator matches the printed line. The signature is
not decoration, it is the entire interface.

The halt line is in the condition for the opposite reason. A halted run never
prints the signature, so a condition matching only the signature would restart
the turn forever against a run that has already stopped and recorded why.

## codex - native goals

codex resolves the same thing through its own goal mechanism, which reads
`thread_goals.objective`. The loop mirrors its immutable `objective` into it,
so the equivalent is the objective handed to bootstrap:

```bash
python3 scripts/init_loop.py <FEATURE> \
  --objective "Run the tlc-loop-tasks loop for feature <FEATURE> until the transcript contains the literal line __TLC_LOOP__ feature=<FEATURE> verify=PASS, or a phase=H action=halt line for that feature."
```

`objective` is written verbatim and is immutable for the rest of the run, so
the run cannot redefine its own success criterion halfway through.

The codex flag that attaches this objective to a goal is deliberately not
written here: the codex environment probe is unresolved
(`references/provider-discovery.md`), and an unverified invocation is worse
than none.

## Neither mechanism available

Use the shell driver. It reads `detect_phase.py` directly rather than the
transcript, so it needs no condition at all:

```bash
bash scripts/loop.sh <FEATURE> --root .
```

It breaks on the same two events: `phase=E` (exit 0) and `phase=H` (exit 1).
