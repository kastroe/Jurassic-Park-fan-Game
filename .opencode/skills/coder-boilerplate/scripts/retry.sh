#!/usr/bin/env bash
# retry.sh — Retry a command with exponential backoff
# Usage: ./retry.sh [max_retries=3] [initial_delay=2] -- <command...>
set -euo pipefail

MAX="${1:-3}"
DELAY="${2:-2}"
shift 2 || true

# Handle the case where -- separates
if [ "${1:-}" = "--" ]; then shift; fi

CMD="$@"
if [ -z "$CMD" ]; then
  echo "Usage: $0 [max_retries=3] [initial_delay=2] -- <command>" >&2
  exit 1
fi

for i in $(seq 1 "$MAX"); do
  if bash -c "$CMD"; then
    exit 0
  fi
  EXIT_CODE=$?
  
  if [ "$i" -lt "$MAX" ]; then
    WAIT=$((DELAY * 2**(i-1)))
    echo "=== Retry $i/$MAX failed (exit $EXIT_CODE). Waiting ${WAIT}s... ===" >&2
    sleep "$WAIT"
  fi
done

echo "=== All $MAX retries failed ===" >&2
exit "$EXIT_CODE"
