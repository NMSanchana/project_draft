#!/usr/bin/env bash
# Ingest everything in ai-service/knowledge_base/ (PDF, TXT, MD) into Qdrant. Safe to re-run:
# unchanged files are skipped, edited files replace their old vectors, deleted files are removed.
# (The running AI service also does this automatically every ~15 s; use this to force it or to see the result.)
set -euo pipefail
source "$(dirname "$0")/_common.sh"
cd "$ROOT/ai-service"
[ -x "$VENV/bin/python" ] || { bad "Python venv missing. Run ./scripts/setup.sh first."; exit 1; }
http_ok "$(env_get .env QDRANT_URL || true)/collections" 2>/dev/null || http_ok http://localhost:6333/collections \
  || { bad "Qdrant is not running -> start Docker Desktop, then: docker compose up -d qdrant"; exit 1; }
"$VENV/bin/python" -m app.rag.ingest
