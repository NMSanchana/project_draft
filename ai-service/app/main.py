"""FastAPI application entry point."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .errors import install_error_handlers
from .routers import chat, datasets, health, ml, pricing, rag, reports

log = logging.getLogger("ai-service")
KB_POLL_SECONDS = 15


def _kb_sync_loop(stop: threading.Event) -> None:
    """Ingest knowledge_base/ at startup and whenever its files change (retries while Qdrant is down)."""
    from .db import session_scope
    from .rag import ingest, store
    from .rag.embeddings import EmbedderUnavailable

    last, warned = None, False
    while not stop.is_set():
        try:
            sig = ingest.folder_signature()
            if sig != last:
                store.ping()
                db = session_scope()
                try:
                    res = ingest.ingest_kb_folder(db)
                finally:
                    db.close()
                last = sig
                if res["ingested"] or res["removed"] or res["errors"]:
                    log.info("Knowledge base synced: %s", res)
        except store.VectorStoreUnavailable:
            log.debug("Knowledge base sync waiting for Qdrant")
        except EmbedderUnavailable as exc:
            if not warned:  # say it once, then keep retrying quietly
                log.warning("Knowledge base sync waiting for the embedding model: %s", exc)
                warned = True
        except Exception:  # noqa: BLE001 - never kill the thread
            log.exception("Knowledge base sync failed")
        stop.wait(KB_POLL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.jwt_secret:
        log.error("JWT_SECRET is empty - every authenticated request will fail. Run scripts/setup.sh.")
    init_db()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    if settings.kb_autosync:
        threading.Thread(target=_kb_sync_loop, args=(stop,), name="kb-sync", daemon=True).start()
    log.info("AI service ready (model=%s, qdrant=%s)", settings.ollama_model, settings.qdrant_url)
    yield
    stop.set()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Business Insight AI Service", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(datasets.router)
    app.include_router(ml.router)
    app.include_router(pricing.router)
    app.include_router(chat.router)
    app.include_router(rag.router)
    app.include_router(reports.router)
    return app


app = create_app()
