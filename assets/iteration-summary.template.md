# tlc-loop-tasks - iteration {{ iteration }}

- **Feature:** {{ feature }}
- **Phase in:** {{ phase_in }} -> **Phase out:** {{ phase_out }}
- **Action:** {{ action }}
- **Outcome:** {{ outcome }} <!-- completed | halted | blocked -->
- **Batch:** {{ batch_label_and_task_ids }} <!-- e.g. P1+P2 / T1,T2,T3 - or n/a -->
- **Gate:** {{ gate_level }} {{ gate_result }} <!-- or n/a -->
- **Checkpoint:** {{ shas_or_skip }} <!-- short SHA per task, "SKIP: no changes", or n/a (phase not B/F) -->
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
When phase_out is E, print this line - and only this line - immediately after
the block, on its own line, as the LAST line of the message:

    __TLC_LOOP__ feature=<feature> verify=PASS

Substitute the real feature name. It is part of the signature: two features
running in one transcript would otherwise satisfy each other's goal condition.

The signature is the interface to every continuation mechanism. A /goal
evaluator, a codex native goal, and a grep in loop.sh all watch for that line,
and none of them can run validate_state.py to find out for themselves.

Never print it for phase_out=H. The signature means verified; a halted or
blocked run is not.
-->
