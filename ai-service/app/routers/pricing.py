"""What-if pricing simulator."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import AppError
from ..ml.pricing import simulate
from ..models import DatasetResult
from ..security import CurrentUser, get_current_user
from .datasets import get_owned_dataset

router = APIRouter(prefix="/ai/v1/pricing", tags=["pricing"])


class SimulateRequest(BaseModel):
    datasetId: str
    segmentValue: str = Field(min_length=1, description="A category/product name, or 'All'")
    priceChangePct: float = Field(ge=-20, le=20, description="Price change in percent, within +-20")


@router.post("/simulate")
def simulate_price(req: SimulateRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Predicted units/revenue/profit change with uncertainty and a reliability flag."""
    ds = get_owned_dataset(db, req.datasetId, user)
    res = db.get(DatasetResult, ds.id)
    pricing = (res.modules if res else {}).get("pricing")
    if pricing is None:
        raise AppError(
            409 if ds.status == "enriching" else 422,
            "Pricing analysis is not ready yet." if ds.status == "enriching" else "No pricing analysis exists for this dataset.",
            "PRICING_NOT_READY",
        )
    if pricing["status"] == "skipped":
        raise AppError(422, pricing["reason"], "PRICING_UNAVAILABLE")
    try:
        return JSONResponse(simulate(pricing, req.segmentValue, req.priceChangePct))
    except KeyError as exc:
        raise AppError(422, f"Unknown segment '{req.segmentValue}'. Available: {exc.args[0]}.", "UNKNOWN_SEGMENT")
    except ValueError as exc:
        raise AppError(422, str(exc), "OUT_OF_BOUNDS")
