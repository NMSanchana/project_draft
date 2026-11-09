#!/usr/bin/env bash
# Check every moving part and print a fix hint for anything that is down.
source "$(dirname "$0")/_common.sh"
cd "$ROOT"
FAIL=0
check() { # check NAME URL HINT
  if http_ok "$2"; then ok "$1"; else bad "$1  ->  $3"; FAIL=1; fi
}
NEST_PORT="$(backend_port)"
check "Frontend      :3000   " http://localhost:3000                      "run ./scripts/start-all.sh (log: logs/frontend.log)"
check "NestJS auth   :$NEST_PORT   " "http://localhost:$NEST_PORT/api/health" "check MONGO_URI in backend/.env; log: logs/backend.log"
check "AI service    :8000   " http://localhost:8000/health               "run ./scripts/start-all.sh (log: logs/ai-service.log)"
check "Qdrant        :6333   " http://localhost:6333/collections          "start Docker Desktop, then: docker compose up -d qdrant"
check "Ollama        :11434  " http://localhost:11434/api/tags            "run: ollama serve"

if http_ok http://localhost:8000/health; then
  H="$(curl -fsS http://localhost:8000/health)"
  echo "   AI service detail: $H"
  case "$H" in *'"ollama":"model_missing"'*) bad "Ollama model missing -> ollama pull $(env_get ai-service/.env OLLAMA_MODEL)"; FAIL=1;; esac
  case "$H" in *'"jwt_configured":false'*) bad "AI service has no JWT_SECRET -> run ./scripts/setup.sh"; FAIL=1;; esac
fi
SA="$(env_get ai-service/.env JWT_SECRET)"; SB="$(env_get backend/.env JWT_SECRET)"; SF="$(env_get frontend/.env.local JWT_SECRET)"
if [ -n "$SA" ] && [ "$SA" = "$SB" ] && [ "$SA" = "$SF" ]; then ok "JWT_SECRET identical in all three .env files"
else bad "JWT_SECRET differs between backend/.env, frontend/.env.local and ai-service/.env -> run ./scripts/setup.sh"; FAIL=1; fi
exit $FAIL
