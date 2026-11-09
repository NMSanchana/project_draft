"""Server-side PDF report download."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import AppError
from ..models import ChatMessage, DatasetResult, KBDocument
from ..rag.ingest import SHARED_USER
from ..reports.pdf import build_report
from ..security import CurrentUser, get_current_user
from .datasets import get_owned_dataset

router = APIRouter(prefix="/ai/v1/datasets", tags=["reports"])


@router.get("/{dataset_id}/report.pdf")
def report_pdf(dataset_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Full PDF report: quality, KPIs, trend, insights, forecast, anomalies, ML modules, documents."""
    ds = get_owned_dataset(db, dataset_id, user)
    if ds.status == "enriching":
        raise AppError(409, "The analysis is still running. Try again in a few seconds.", "NOT_READY")
    res = db.get(DatasetResult, ds.id)
    if res is None:
        raise AppError(404, "No results exist for this dataset.", "DATASET_NOT_FOUND")
    docs = [
        {"fileName": d.file_name, "scope": d.scope, "shared": d.scope == "shared", "chunks": d.chunks}
        for d in db.query(KBDocument).filter((KBDocument.user_id == user.id) | (KBDocument.user_id == SHARED_USER)).all()
    ]
    cited: set[str] = set()
    for m in (
        db.query(ChatMessage).filter(ChatMessage.dataset_id == ds.id, ChatMessage.user_id == user.id, ChatMessage.role == "assistant").all()
    ):
        cited.update(x.split("#")[0].removeprefix("doc:") for x in (m.sources or []) if str(x).startswith("doc:"))
    pdf = build_report(ds.file_name, dict(res.analytics), dict(res.modules), docs, sorted(cited))
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", ds.file_name.rsplit(".", 1)[0]) or "report"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="insight-report-{name}.pdf"'})
