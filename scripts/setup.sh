#!/usr/bin/env bash
# First-time setup. Safe to re-run (idempotent).
set -euo pipefail
source "$(dirname "$0")/_common.sh"
cd "$ROOT"

step "1/6 Checking prerequisites"
MISSING=0
if have node; then
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$NODE_MAJOR" -ge 20 ]; then ok "Node $(node -v)"; else bad "Node $(node -v) is too old (need >= 20). Install: brew install node"; MISSING=1; fi
else bad "Node.js not found. Install: brew install node"; MISSING=1; fi

PY=""
for cand in python3.12 python3.11 python3; do
  if have "$cand" && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then PY="$cand"; break; fi
done
if [ -n "$PY" ]; then ok "Python $($PY --version 2>&1 | cut -d' ' -f2) ($PY)"; else bad "Python 3.11+ not found. Install: brew install python@3.12"; MISSING=1; fi

if have docker && docker info >/dev/null 2>&1; then ok "Docker is running"
else warn "Docker is not running/installed - Qdrant (documents RAG) will be unavailable. Install Docker Desktop and start it."; fi
if have ollama; then ok "Ollama installed"
else warn "Ollama not found - AI-written insights and chat phrasing will fall back to templates. Install: brew install ollama"; fi
[ "$MISSING" -eq 0 ] || { bad "Fix the items above and re-run ./scripts/setup.sh"; exit 1; }

step "2/6 Environment files (one shared JWT_SECRET)"
SECRET="$(env_get ai-service/.env JWT_SECRET)"
for f in backend/.env frontend/.env.local; do
  [ -n "$SECRET" ] && [ "$SECRET" != "change_me" ] && break
  SECRET="$(env_get "$f" JWT_SECRET)"
  case "$SECRET" in your_jwt_secret_here|change_me) SECRET="";; esac
done
if [ -z "$SECRET" ] || [ "$SECRET" = "change_me" ]; then
  SECRET="$($PY -c 'import secrets; print(secrets.token_hex(32))')"
  ok "Generated a new random JWT_SECRET"
else ok "Re-using the existing JWT_SECRET"; fi

[ -f backend/.env ]          || cp backend/.env.example backend/.env
[ -f frontend/.env.local ]   || cp frontend/.env.example frontend/.env.local
[ -f ai-service/.env ]       || cp ai-service/.env.example ai-service/.env
for f in backend/.env frontend/.env.local ai-service/.env; do env_set "$f" JWT_SECRET "$SECRET"; done
ok "JWT_SECRET written to backend/.env, frontend/.env.local, ai-service/.env"
if grep -q '<username>' backend/.env; then
  warn "backend/.env still has the MONGO_URI placeholder. Edit it with your MongoDB Atlas/local URI before starting."
fi

step "3/6 Python virtualenv + pinned dependencies (ai-service)"
[ -d "$VENV" ] || "$PY" -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r ai-service/requirements.txt
ok "Python dependencies installed"

step "4/6 Node dependencies"
# NOTE: 'npm install' (not 'npm ci') because the frontend lockfile is out of sync with package.json.
(cd backend  && npm install --no-audit --no-fund --loglevel=error) && ok "backend deps"
(cd frontend && npm install --no-audit --no-fund --loglevel=error) && ok "frontend deps"

step "5/6 Local LLM model"
MODEL="$(env_get ai-service/.env OLLAMA_MODEL)"; MODEL="${MODEL:-llama3.2:3b}"
if have ollama; then
  if ! http_ok http://localhost:11434/api/tags; then
    warn "Ollama server is not running; starting it in the background..."
    nohup ollama serve >/dev/null 2>&1 & sleep 4
  fi
  if http_ok http://localhost:11434/api/tags; then ollama pull "$MODEL" && ok "Model $MODEL ready"
  else warn "Could not reach Ollama. Run 'ollama serve' in another terminal, then 'ollama pull $MODEL'."; fi
else warn "Skipping model pull (Ollama not installed)."; fi

step "6/6 Embedding model (for documents / RAG)"
if "$VENV/bin/python" -c "import sentence_transformers" 2>/dev/null; then
  (cd ai-service && "$VENV/bin/python" -c "from app.rag.embeddings import warm_up; warm_up()") && ok "Embedding model downloaded (~90 MB, one time)"
else warn "RAG dependencies are not part of this build yet - skipping."; fi

echo
ok "Setup complete. Next: ./scripts/start-all.sh   (then open http://localhost:3000)"
