#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT=8765

stop_pid() {
    local pid="$1"
    [[ -n "$pid" ]] || return 0
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        sleep 0.5
        kill -9 "$pid" 2>/dev/null || true
        echo "Laboratório Personas LLM encerrado (PID $pid)."
        return 0
    fi
    return 1
}

stopped=0
for PID_FILE in "$ROOT/.lab-personas-llm.pid" "$ROOT/.debates.pid"; do
    if [[ -f "$PID_FILE" ]]; then
        if stop_pid "$(cat "$PID_FILE")"; then
            stopped=1
        fi
        rm -f "$PID_FILE"
    fi
done

while read -r pid; do
    [[ -z "$pid" ]] && continue
    stop_pid "$pid" && stopped=1
done < <(lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null || true)

if [[ "$stopped" -eq 0 ]]; then
    echo "Nenhuma instância rodando."
fi
