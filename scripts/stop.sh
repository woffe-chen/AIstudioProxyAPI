#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$REPO_DIR/run"
PID_FILE="$RUN_DIR/aistudio_proxy.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "No PID file found at $PID_FILE. Service may not be running." >&2
    exit 1
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" >/dev/null 2>&1; then
    echo "Process $PID not running; removing stale PID file." >&2
    rm -f "$PID_FILE"
    exit 1
fi

kill "$PID"
echo "Sent TERM to process $PID. Waiting for exit..."
wait "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "Service stopped."
