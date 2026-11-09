"""Dataset endpoints: analyze (fast phase), poll, list, delete."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..errors import AppError
from ..models import ChatMessage, Conversation, Dataset, DatasetResult, KBDocument
from ..pipeline.assemble import run_fast_phase
from ..pipeline.enrichment import run_enrichment
from ..pipeline.ingest import DataError, sanitize_filename
from ..rag import store as rag_store
from ..schemas import DatasetSummary
from ..security import CurrentUser, get_current_user
from ..storage import delete_dataset_files, save_dataset_files

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/v1/datasets", tags=["datasets"])


def get_owned_dataset(db: Session, dataset_id: str, user: CurrentUser) -> Dataset:
    """Fetch a dataset the caller owns: 404 if unknown, 403 if it belongs to someone else."""
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise AppError(404, "Dataset not found.", "DATASET_NOT_FOUND")
    if ds.user_id != user.id:
        raise AppError(403, "You do not have access to this dataset.", "FORBIDDEN")
    return ds


def _read_upload(file: UploadFile, settings: Settings) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise AppError(415, "Only .csv files are supported.", "UNSUPPORTED_MEDIA_TYPE")
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise AppError(413, f"File is larger than the {settings.max_upload_mb} MB limit.", "FILE_TOO_LARGE")
    return data


@router.post("/analyze")
def analyze(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    business_name: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Fast phase: returns a complete ProcessedAnalytics, then enriches in the background."""
    raw = _read_upload(file, settings)
    safe_name = sanitize_filename(file.filename)
    ds = Dataset(id=uuid.uuid4().hex, user_id=user.id, file_name=safe_name, business_name=(business_name or None), status="enriching")
    try:
        fast = run_fast_phase(raw, safe_name, ds.id)
    except DataError as exc:
        raise AppError(422, str(exc), "INVALID_DATA") from exc

    ds.rows = fast.kpis["rows"]
    save_dataset_files(user.id, ds.id, raw, safe_name, fast.clean_df)
    db.add(ds)
    db.add(
        DatasetResult(
            dataset_id=ds.id,
            analytics=fast.analytics,
            modules={"quality": fast.clean_result.report},
            timings={"fast_phase": round(fast.seconds, 2)},
        )
    )
    db.commit()
    background.add_task(run_enrichment, ds.id)
    return JSONResponse(fast.analytics)


@router.get("")
def list_datasets(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DatasetSummary]:
    rows = db.query(Dataset).filter(Dataset.user_id == user.id).order_by(Dataset.created_at.desc()).all()
    return [
        DatasetSummary(datasetId=d.id, fileName=d.file_name, status=d.status, rows=d.rows, createdAt=d.created_at.isoformat()) for d in rows
    ]


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Latest full result. ``status`` is ``enriching`` | ``ready`` | ``failed``."""
    ds = get_owned_dataset(db, dataset_id, user)
    res = db.get(DatasetResult, ds.id)
    body = dict(res.analytics if res else {})
    body["status"], body["datasetId"] = ds.status, ds.id
    if ds.stage:
        body["stage"] = ds.stage
    if ds.status == "failed":
        body["error"] = ds.error
    return JSONResponse(body)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove the dataset's result, files, chat history and its Qdrant collection."""
    ds = get_owned_dataset(db, dataset_id, user)
    db.execute(delete(ChatMessage).where(ChatMessage.dataset_id == ds.id))
    db.execute(delete(Conversation).where(Conversation.dataset_id == ds.id))
    db.execute(delete(KBDocument).where(KBDocument.dataset_id == ds.id))
    db.delete(ds)
    db.commit()
    delete_dataset_files(user.id, dataset_id)
    vectors_removed = True
    try:
        rag_store.delete_collection(rag_store.data_collection(dataset_id))
    except rag_store.VectorStoreUnavailable:
        vectors_removed = False
        log.warning("Qdrant unavailable: vectors for dataset %s were not removed", dataset_id)
    return {"success": True, "message": "Dataset deleted.", "vectorsRemoved": vectors_removed}
