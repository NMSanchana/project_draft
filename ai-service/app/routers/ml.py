"""Detailed module output for chat, docs and future UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import AppError
from ..models import DatasetResult
from ..security import CurrentUser, get_current_user
from .datasets import get_owned_dataset

router = APIRouter(prefix="/ai/v1/datasets", tags=["ml"])
MODULES = {"segments", "churn", "drivers", "pricing", "basket", "forecast", "anomalies"}


@router.get("/{dataset_id}/ml/{module}")
def get_module(dataset_id: str, module: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Full JSON for one module. ``status`` is ok | unreliable | skipped | pending | failed."""
    if module not in MODULES:
        raise AppError(404, f"Unknown module '{module}'. Choose one of: {', '.join(sorted(MODULES))}.", "UNKNOWN_MODULE")
    ds = get_owned_dataset(db, dataset_id, user)
    res = db.get(DatasetResult, ds.id)
    data = (res.modules if res else {}).get(module)
    if data is None:
        if ds.status == "enriching":
            return JSONResponse({"status": "pending", "reason": "Analysis is still running; try again shortly."})
        return JSONResponse({"status": "skipped", "reason": f"The '{module}' module has not produced results for this dataset."})
    return JSONResponse(data)
