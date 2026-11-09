"""Document (RAG) management: upload, list, delete."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..errors import AppError
from ..models import KBDocument
from ..rag.embeddings import EmbedderUnavailable
from ..rag.ingest import ALLOWED, SHARED_USER, DocumentError, delete_document, ingest_bytes
from ..rag.store import VectorStoreUnavailable
from ..security import CurrentUser, get_current_user
from .datasets import get_owned_dataset

router = APIRouter(prefix="/ai/v1/rag", tags=["rag"])
DOWN = "Document search is unavailable: the vector database (Qdrant) is not running. Start it with `docker compose up -d qdrant`."


def _row(d: KBDocument) -> dict:
    return {
        "id": d.id,
        "fileName": d.file_name,
        "scope": d.scope,
        "datasetId": d.dataset_id,
        "chunks": d.chunks,
        "shared": d.scope == "shared",
        "createdAt": d.created_at.isoformat(),
    }


@router.post("/documents")
def upload_document(
    file: UploadFile = File(...),
    scope: str = Form(default="user"),
    datasetId: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Ingest a PDF/TXT/MD. ``scope=user`` is private to you; ``scope=dataset`` is tied to one dataset (needs ``datasetId``)."""
    name = (file.filename or "").lower()
    if not any(name.endswith(e) for e in ALLOWED):
        raise AppError(415, "Only .pdf, .txt and .md documents are supported.", "UNSUPPORTED_MEDIA_TYPE")
    if scope not in ("user", "dataset"):
        raise AppError(422, "scope must be 'user' or 'dataset'.", "VALIDATION_ERROR")
    if scope == "dataset":
        if not datasetId:
            raise AppError(422, "datasetId is required when scope=dataset.", "VALIDATION_ERROR")
        get_owned_dataset(db, datasetId, user)
    raw = file.file.read(settings.max_upload_bytes + 1)
    if len(raw) > settings.max_upload_bytes:
        raise AppError(413, f"File is larger than the {settings.max_upload_mb} MB limit.", "FILE_TOO_LARGE")
    try:
        return ingest_bytes(db, raw, file.filename or "document.txt", user_id=user.id, scope=scope, dataset_id=datasetId)
    except DocumentError as exc:
        raise AppError(422, str(exc), "INVALID_DOCUMENT") from exc
    except VectorStoreUnavailable as exc:
        db.rollback()
        raise AppError(503, DOWN, "VECTOR_DB_DOWN") from exc
    except EmbedderUnavailable as exc:
        db.rollback()
        raise AppError(503, str(exc), "EMBEDDER_UNAVAILABLE") from exc


@router.get("/documents")
def list_documents(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Your documents plus the shared knowledge_base/ files (``shared: true``)."""
    rows = (
        db.query(KBDocument)
        .filter((KBDocument.user_id == user.id) | (KBDocument.user_id == SHARED_USER))
        .order_by(KBDocument.created_at.desc())
        .all()
    )
    return [_row(d) for d in rows]


@router.delete("/documents/{doc_id}")
def remove_document(doc_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(KBDocument, doc_id)
    if doc is None:
        raise AppError(404, "Document not found.", "DOCUMENT_NOT_FOUND")
    if doc.scope == "shared":
        raise AppError(403, "Shared knowledge-base files are managed by adding/removing them in the knowledge_base folder.", "FORBIDDEN")
    if doc.user_id != user.id:
        raise AppError(403, "You do not have access to this document.", "FORBIDDEN")
    try:
        delete_document(db, doc)
    except VectorStoreUnavailable as exc:
        db.rollback()
        raise AppError(503, DOWN, "VECTOR_DB_DOWN") from exc
    return {"success": True, "message": "Document deleted."}
