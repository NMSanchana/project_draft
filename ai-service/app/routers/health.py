"""Liveness + dependency status. Never raises if Ollama/Qdrant are down."""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from ..config import get_settings
from ..db import session_scope

router = APIRouter(tags=["health"])


def _probe(url: str) -> dict | None:
    try:
        r = httpx.get(url, timeout=1.5)
        return r.json() if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


@router.get("/health")
def health() -> dict:
    s = get_settings()
    try:
        db = session_scope()
        try:
            db.execute(text("SELECT 1"))
            db_state = "up"
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        db_state = "down"

    qdrant = "up" if _probe(f"{s.qdrant_url.rstrip('/')}/collections") is not None else "down"
    tags = _probe(f"{s.ollama_url.rstrip('/')}/api/tags")
    if tags is None:
        ollama = "down"
    else:
        names = [m.get("name", "") for m in tags.get("models", [])]
        ollama = "up" if any(n == s.ollama_model or n.startswith(s.ollama_model + ":") for n in names) else "model_missing"

    try:
        from .. import rag  # noqa: F401
        from ..rag import embeddings

        loaded = bool(getattr(embeddings, "is_loaded", lambda: False)())
    except Exception:  # noqa: BLE001
        loaded = False
    return {
        "status": "ok" if db_state == "up" else "degraded",
        "db": db_state,
        "qdrant": qdrant,
        "ollama": ollama,
        "model": s.ollama_model,
        "embedder_loaded": loaded,
        "jwt_configured": bool(s.jwt_secret),
    }
