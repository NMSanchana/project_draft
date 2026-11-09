#!/usr/bin/env bash
# Shared helpers (sourced by the other scripts).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
PID_DIR="$ROOT/.pids"
VENV="$ROOT/ai-service/.venv"

if [ -t 1 ]; then G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; B=$'\033[1m'; N=$'\033[0m'; else G=""; R=""; Y=""; B=""; N=""; fi
ok()   { echo "${G}✔${N} $*"; }
bad()  { echo "${R}✘${N} $*"; }
warn() { echo "${Y}!${N} $*"; }
step() { echo; echo "${B}==> $*${N}"; }
have() { command -v "$1" >/dev/null 2>&1; }

# env_get FILE KEY  -> prints value (empty if missing)
env_get() { [ -f "$1" ] && grep -E "^$2=" "$1" | tail -1 | cut -d= -f2- || true; }

# env_set FILE KEY VALUE (portable: no sed -i differences between macOS and Linux)
env_set() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys, re, pathlib
path, key, value = sys.argv[1:4]
p = pathlib.Path(path)
lines = p.read_text().splitlines() if p.exists() else []
out, done = [], False
for ln in lines:
    if re.match(rf"^{re.escape(key)}=", ln):
        out.append(f"{key}={value}"); done = True
    else:
        out.append(ln)
if not done:
    out.append(f"{key}={value}")
p.write_text("\n".join(out) + "\n")
PY
}

# http_ok URL -> 0 if a GET returns 2xx
http_ok() { curl -fsS --max-time 3 "$1" >/dev/null 2>&1; }

backend_port() { local p; p="$(env_get "$ROOT/backend/.env" PORT)"; echo "${p:-5000}"; }
