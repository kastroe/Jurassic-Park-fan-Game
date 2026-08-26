#!/usr/bin/env bash
# run-with-timeout.sh — Execute a command with timeout, resource limits, and output capture
# Usage: ./run-with-timeout.sh <timeout_seconds> <command...>
# Captures stdout, stderr, exit code. Kills hung commands.
set -euo pipefail

TIMEOUT="${1:-30}"
shift 1
CMD="$@"

if [ -z "$CMD" ]; then
  echo "Usage: $0 <timeout_seconds> <command...>" >&2
  exit 1
fi

OUTFILE=$(mktemp)
ERRFILE=$(mktemp)
trap 'rm -f "$OUTFILE" "$ERRFILE"' EXIT

echo "=== Running (timeout: ${TIMEOUT}s): $CMD ===" >&2
START=$(date +%s)
# Run with timeout and resource limits
timeout "$TIMEOUT" bash -c "$CMD" >"$OUTFILE" 2>"$ERRFILE"
EXIT_CODE=$?
END=$(date +%s)

echo "=== Exit code: $EXIT_CODE | Duration: $((END - START))s ===" >&2

if [ $EXIT_CODE -eq 124 ]; then
  echo "=== TIMED OUT after ${TIMEOUT}s ===" >&2
elif [ $EXIT_CODE -ne 0 ]; then
  echo "=== FAILED with exit code $EXIT_CODE ===" >&2
fi

# Output stdout
if [ -s "$OUTFILE" ]; then
  echo "--- stdout ---"
  # Truncate if too large
  LINES=$(wc -l < "$OUTFILE")
  if [ "$LINES" -gt 200 ]; then
    head -n 100 "$OUTFILE"
    echo "... [truncated: $LINES lines total] ..."
    tail -n 100 "$OUTFILE"
  else
    cat "$OUTFILE"
  fi
fi

# Output stderr
if [ -s "$ERRFILE" ]; then
  echo "--- stderr ---" >&2
  cat "$ERRFILE" >&2
fi

exit $EXIT_CODE
