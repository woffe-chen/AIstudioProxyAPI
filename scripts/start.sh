#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO_DIR/logs"
RUN_DIR="$REPO_DIR/run"
PID_FILE="$RUN_DIR/aistudio_proxy.pid"
LOG_FILE="$LOG_DIR/headless.log"

if ! command -v lsof >/dev/null 2>&1; then
    echo "lsof is required for port cleanup but was not found in PATH." >&2
    exit 1
fi

terminate_pid() {
    local pid="$1"
    local desc="$2"

    if ! kill -0 "$pid" >/dev/null 2>&1; then
        return
    fi

    echo " - Sending SIGTERM to PID $pid ($desc)"
    kill "$pid" >/dev/null 2>&1 || true

    local end=$((SECONDS + 5))
    while kill -0 "$pid" >/dev/null 2>&1 && (( SECONDS < end )); do
        sleep 0.2
    done

    if kill -0 "$pid" >/dev/null 2>&1; then
        echo " - PID $pid ignored SIGTERM; forcing SIGKILL"
        kill -9 "$pid" >/dev/null 2>&1 || true
    fi
}

is_repo_process() {
    local cmd="$1"

    if [[ "$cmd" == *"$REPO_DIR"* ]]; then
        return 0
    fi

    case "$cmd" in
        *launch_camoufox.py*|*proxy_server.py*|*Camoufox*|*camoufox*|*AIstudioProxyAPI*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

cleanup_port() {
    local port="$1"
    local pids=()

    mapfile -t pids < <(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | sort -u)
    if [[ ${#pids[@]} -eq 0 ]]; then
        return
    fi

    echo "Port $port is currently in use by: ${pids[*]}"
    for pid in "${pids[@]}"; do
        if [[ -z "$pid" ]]; then
            continue
        fi
        if ! ps -p "$pid" >/dev/null 2>&1; then
            continue
        fi

        local cmdline
        cmdline="$(ps -p "$pid" -o args= 2>/dev/null | tr -d '\n')"

        if is_repo_process "$cmdline"; then
            terminate_pid "$pid" "$cmdline"
        else
            echo "Port $port is occupied by PID $pid ($cmdline) which is outside $REPO_DIR." >&2
            echo "Cannot auto-clean; please free the port manually." >&2
            exit 1
        fi
    done
}

mkdir -p "$LOG_DIR" "$RUN_DIR"

if [[ -f "$PID_FILE" ]]; then
    PID="$(cat "$PID_FILE")"
    if kill -0 "$PID" >/dev/null 2>&1; then
        echo "Service already running with PID $PID (see $PID_FILE). Use scripts/stop.sh first." >&2
        exit 1
    fi
    rm -f "$PID_FILE"
fi

TARGET_PORTS=(2048 3120 9222)
for port in "${TARGET_PORTS[@]}"; do
    cleanup_port "$port"
done

cd "$REPO_DIR"
nohup poetry run python launch_camoufox.py --headless >>"$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" >"$PID_FILE"
echo "Service started with PID $NEW_PID. Logs: $LOG_FILE"
