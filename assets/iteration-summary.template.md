# tlc-loop - iteration {{ iteration }}

- **Feature:** {{ feature }}
- **Phase in:** {{ phase_in }} -> **Phase out:** {{ phase_out }}
- **Action:** {{ action }}
- **Outcome:** {{ outcome }} <!-- completed | halted | blocked -->
- **Batch:** {{ batch_label_and_task_ids }} <!-- e.g. P1+P2 / T1,T2,T3 - or n/a -->
- **Gate:** {{ gate_level }} {{ gate_result }} <!-- or n/a -->
- **Checkpoint:** {{ shas }} <!-- short SHA per task, "<sha> empty" for a task that changed nothing, or n/a (phase not B/F) -->
- **Verify:** {{ verdict_and_report_path }} <!-- PASS|FAIL + validation.md path, or n/a -->
- **Halt reason:** {{ reason_and_detail_or_none }}
- **State:** {{ update_loop_output_line }} <!-- the "updated feature=... iteration=N status=..." line -->
- **Next phase per detect_phase.py:** {{ next_phase }}

<!--
Substitution template. Nothing renders these placeholders; fill them in.

WHEN TO PRINT
Once per completed iteration, after the phase action and after the checklist in
references/checklist.md passes.

Intermediate failures do NOT render this block. A failed command, gate, or
executor stays inside the phase action: diagnose and repair it per
references/recovery-loop.md, then print one block for the iteration that
finally closed. A block per repair attempt would turn a repaired failure into
what looks like a stalled run.

AFTER PRINTING
phase_out is neither E nor H  -> re-enter detection in the same turn.
phase_out is E or H           -> stop.

DONE-SIGNATURE
Never write the signature yourself, here or anywhere. When phase_out is E, run
the finalizer immediately after this block:

    python3 <skill-dir>/scripts/finish_loop.py <feature> --root <root>

It re-derives the situation, records completion through update_loop.py, checks
that nothing moved underneath it, and prints the signature as the last line of
output. Exit 2 is a refusal naming what is wrong - repair the cause and re-enter
detection rather than printing anything in its place.

The signature is the interface to every continuation mechanism. A /goal
evaluator, a codex native goal, and a grep in loop.sh all watch for that line,
and none of them can run validate_state.py to find out for themselves. That is
exactly why one script owns it: matching the line has to be equivalent to
trusting a deterministic check, not to trusting a summary.

It is never printed for phase_out=H. The signature means verified; a halted or
blocked run is not - and finish_loop.py refuses on anything but phase=E.
-->
