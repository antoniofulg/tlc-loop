#!/usr/bin/env bash
#
# loop.sh - portable restart driver for harnesses with no native goal mechanism.
#
# Claude Code has `/goal` and codex has native goals: both restart the next turn
# on their own, so they do not need this. Anything else does. The driver is
# deliberately dumb - it reads one line from `detect_phase.py` and either stops
# or respawns an agent - because every decision worth making already happens in
# the scripts and the skill.
#
# One iteration:
#
#   1. Run detect_phase.py and read its single line.
#   2. phase=E  -> print the line, exit 0. The feature is done.
#      phase=H  -> print the line, exit 1. The run stopped for a recorded reason.
#      anything else -> resolve `continue.respawn` and spawn it, then repeat.
#
# It never spins. A line it cannot parse, a detect that fails, a respawn it
# cannot resolve, and a respawn that exits non-zero all stop the driver with
# exit 2. Retrying any of them would hammer the same failure with no counter
# advancing anywhere, because the counters live in `loop.json` and only
# `update_loop.py` writes them.
#
# The one clock it owns: when the resolved line carries `timeout=<seconds>`
# (`limits.executor_timeout_seconds`), a respawn that outlives it is killed.
# The driver does not hold that clock itself - `_spawn.py` does, because shell
# job control is the wrong tool for it and two attempts here proved it. An
# expiry is an executor failure, not a retry condition: it is recorded through
# `update_loop.py --halt executor`, and the next detect turns that into the
# `phase=H` line the driver already knows how to stop on. A hung provider CLI
# is otherwise silence until somebody comes back and looks.
#
# Usage:
#     loop.sh <feature> [--root DIR]
#
# Exit codes:
#     0  broke on phase=E
#     1  broke on phase=H
#     2  the driver could not continue (bad invocation, unreadable detect line,
#        unresolvable or failing respawn)
#
# Environment overrides, all optional:
#     LOOP_DETECT_CMD   command that prints the phase line
#     LOOP_RESOLVE_CMD  command that resolves a stage
#     LOOP_UPDATE_CMD   command that records a halt in loop.json
#     LOOP_PROMPT       payload text handed to the respawned agent
#     LOOP_EVIDENCE     evidence file path; a temp file is used when unset
#
# Driver chatter goes to stderr and phase lines go to stdout, so the last line
# of stdout is always the line the driver broke on.

set -u

self_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)

: "${LOOP_DETECT_CMD:=python3 ${self_dir}/detect_phase.py}"
: "${LOOP_RESOLVE_CMD:=python3 ${self_dir}/resolve_stage.py}"
: "${LOOP_UPDATE_CMD:=python3 ${self_dir}/update_loop.py}"
: "${LOOP_PROMPT:=}"
: "${LOOP_EVIDENCE:=}"

newline='
'

# What a killed respawn reports. 124 is the value timeout(1) uses for the same
# event, kept so the number means the same thing to anyone reading a transcript.
# `_spawn.py` returns it; this is the driver's copy of the contract.
TIMED_OUT=124

usage() {
    cat <<'EOF'
usage: loop.sh <feature> [--root DIR]

Drives detect_phase.py until it reports phase=E (exit 0) or phase=H (exit 1).
Every other phase respawns the continue.respawn agent and detection runs again.
EOF
}

die() {
    code=$1
    shift
    printf 'loop.sh: %s\n' "$*" >&2
    exit "$code"
}

# Run a command string, killing it after $1 seconds. An empty $1 means
# unlimited: the command runs in the foreground of this shell, with no spawner
# and no clock involved at all. Returns the command's own status, or $TIMED_OUT.
#
# A bound hands the command to `_spawn.py`, which runs it in a session of its
# own and kills that whole session on expiry. Bash cannot do this correctly:
# `set -m` makes the respawn a *background* job of the driver's terminal, the
# kernel stops it with SIGTTIN the moment it reads that terminal, and a stopped
# child is one `wait` never returns from. Two watchdogs were written here and
# both were wrong. The third one is not written in bash.
run_bounded() {
    bounded_secs=$1
    bounded_cmd=$2

    if [ -z "$bounded_secs" ]; then
        # The resolver emits a shell-quoted command line, so eval is how it is
        # meant to be run. What it contains comes from the user's own config.
        eval "$bounded_cmd"
        return $?
    fi

    python3 "${self_dir}/_spawn.py" --timeout "$bounded_secs" -- "$bounded_cmd"
}

# Record a halt through the single writer, then let detection report it. The
# driver never prints a stop the vocabulary does not already cover.
record_halt() {
    printf 'loop.sh: recording halt reason=%s: %s\n' "$1" "$2" >&2
    if ! $LOOP_UPDATE_CMD "$feature" --root "$root" --halt "$1" --detail "$2" >/dev/null; then
        die 2 "could not record the $1 halt; stopping"
    fi
}

feature=
root=.

while [ "$#" -gt 0 ]; do
    case $1 in
        --root)
            [ "$#" -ge 2 ] || die 2 "--root needs a directory"
            root=$2
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        -*)
            die 2 "unknown option $1"
            ;;
        *)
            [ -z "$feature" ] || die 2 "only one feature may be given (got '$feature' and '$1')"
            feature=$1
            shift
            ;;
    esac
done

if [ -z "$feature" ]; then
    usage >&2
    exit 2
fi

if [ -z "$LOOP_PROMPT" ]; then
    LOOP_PROMPT="Use the tlc-loop skill to continue the loop for feature ${feature} in ${root}: detect the phase, run exactly one phase action, then continue."
fi

# codex writes its result to a file rather than a stream, so the resolver needs
# somewhere to point it. A temp file keeps it out of the worktree: a stray file
# under the repo root is an uncommitted change mapping to no task, which is
# itself a halt condition.
if [ -z "$LOOP_EVIDENCE" ]; then
    LOOP_EVIDENCE=$(mktemp "${TMPDIR:-/tmp}/tlc-loop-evidence-XXXXXX") ||
        die 2 "could not create an evidence file"
    trap 'rm -f "$LOOP_EVIDENCE"' EXIT
fi

while :; do
    # Unquoted on purpose: the command is a string so it can carry the
    # interpreter and the script path, and so a test can substitute a stub.
    if ! line=$($LOOP_DETECT_CMD "$feature" --root "$root"); then
        die 2 "detect_phase exited non-zero; stopping rather than spinning"
    fi

    case $line in
        *"$newline"*) phase= ;;
        phase=*)
            phase=${line#phase=}
            phase=${phase%% *}
            ;;
        *) phase= ;;
    esac

    case $phase in
        0 | B | V | F | E | H) ;;
        *) die 2 "cannot parse the detect line; stopping rather than spinning: ${line}" ;;
    esac

    printf '%s\n' "$line"

    [ "$phase" != E ] || exit 0
    [ "$phase" != H ] || exit 1

    if ! resolved=$($LOOP_RESOLVE_CMD --stage continue.respawn --root "$root" \
        --feature "$feature" --prompt "$LOOP_PROMPT" --evidence "$LOOP_EVIDENCE"); then
        die 2 "could not resolve continue.respawn; stopping"
    fi

    # Absent means unlimited, the same as omitting the key (D8).
    case $resolved in
        *" timeout="*)
            secs=${resolved#*" timeout="}
            secs=${secs%% *}
            ;;
        *) secs= ;;
    esac

    case $resolved in
        *" cmd="*) cmd=${resolved#*" cmd="} ;;
        *) die 2 "continue.respawn resolved to '${resolved}', which is nothing this driver can spawn; name a CLI in continue.respawn.provider" ;;
    esac
    [ -n "$cmd" ] || die 2 "continue.respawn resolved to an empty command"

    printf 'loop.sh: respawn %s\n' "$cmd" >&2

    run_bounded "$secs" "$cmd"
    status=$?

    if [ "$status" -eq "$TIMED_OUT" ]; then
        record_halt executor \
            "continue.respawn exceeded limits.executor_timeout_seconds (${secs}s) and was killed"
        continue
    fi
    [ "$status" -eq 0 ] ||
        die 2 "respawn command exited ${status}; stopping rather than spinning"
done
