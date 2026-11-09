#!/usr/bin/env bash
# Start everything: Qdrant, Ollama, AI service, NestJS, Next.js. Safe to re-run.
set -uo pipefail
source "$(dirname "$0")/_common.sh"
cd "$ROOT"
mkdir -p "$LOG_DIR" "$PID_DIR"

[ -f ai-service/.env ] && [ -f backend/.env ] && [ -f frontend/.env.local ] || { bad "Not set up yet. Run ./scripts/setup.sh first."; exit 1; }
[ -x "$VENV/bin/uvicorn" ] || { bad "Python venv missing. Run ./scripts/setup.sh first."; exit 1; }

is_running() { [ -f "$PID_DIR/$1.pid" ] && kill -0 "$(cat "$PID_DIR/$1.pid")" 2>/dev/null; }
launch() { # launch NAME DIR CMD...
  local name="$1" dir="$2"; shift 2
  if is_running "$name"; then ok "$name already running (pid $(cat "$PID_DIR/$name.pid"))"; return; fi
  (cd "$dir" && nohup "$@" >"$LOG_DIR/$name.log" 2>&1 & echo $! >"$PID_DIR/$name.pid")
  ok "started $name (log: logs/$name.log)"
}
wait_for() { # wait_for NAME URL SECONDS
  for _ in $(seq 1 "$3"); do http_ok "$2" && { ok "$1 is up"; return 0; }; sleep 1; done
  bad "$1 did not come up in $3s - see logs/$(echo "$1" | tr 'A-Z ' 'a-z-').log"; return 1
}

step "Qdrant (vector database)"
if have docker && docker info >/dev/null 2>&1; then
  docker compose up -d qdrant >/dev/null 2>&1 && ok "Qdrant container started" || warn "Could not start Qdrant via docker compose"
else warn "Docker not running -> document Q&A (RAG) disabled. Start Docker Desktop and re-run."; fi

step "Ollama (local LLM)"
if http_ok http://localhost:11434/api/tags; then ok "Ollama already running"
elif have ollama; then nohup ollama serve >"$LOG_DIR/ollama.log" 2>&1 & echo $! >"$PID_DIR/ollama.pid"; sleep 3; ok "Ollama started"
else warn "Ollama not installed -> template fallback will be used instead of the LLM."; fi

step "AI service (FastAPI :8000)"
launch ai-service ai-service "$VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000

step "NestJS backend (auth)"
NEST_PORT="$(backend_port)"
launch backend backend npm run start:dev

step "Next.js frontend"
launch frontend frontend npm run dev

step "Waiting for services"
wait_for "AI service" http://localhost:8000/health 60
wait_for "Backend" "http://localhost:$NEST_PORT/api/health" 90 || warn "Backend needs a valid MONGO_URI in backend/.env (see RUN_GUIDE.md)."
wait_for "Frontend" http://localhost:3000 90

echo
echo "${B}Open:${N}  App http://localhost:3000   |  AI API docs http://localhost:8000/docs   |  Logs: ./logs"
echo "Stop with ./scripts/stop-all.sh   Check with ./scripts/healthcheck.sh"
