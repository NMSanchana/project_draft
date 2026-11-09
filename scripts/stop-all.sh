#!/usr/bin/env bash
# Stop everything started by start-all.sh.
source "$(dirname "$0")/_common.sh"
cd "$ROOT"

kill_tree() {
  local pid="$1"
  for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child"; done
  kill "$pid" 2>/dev/null || true
}
for name in frontend backend ai-service ollama; do
  f="$PID_DIR/$name.pid"
  if [ -f "$f" ]; then
    pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then kill_tree "$pid"; ok "stopped $name"; else warn "$name was not running"; fi
    rm -f "$f"
  fi
done
if have docker && docker info >/dev/null 2>&1; then docker compose stop qdrant >/dev/null 2>&1 && ok "stopped qdrant"; fi
echo "Done. (Ollama is only stopped if this tooling started it.)"
