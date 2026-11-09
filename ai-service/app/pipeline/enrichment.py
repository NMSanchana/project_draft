"""Phase 2 (background): optional heavy stages. One failing stage never fails the dataset.

Stages are registered as ``(name, callable(ctx))``. ``ctx`` is an :class:`EnrichmentContext`
holding the cleaned frame and the mutable analytics/modules dictionaries.
"""

from __future__ import annotations

import copy
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from ..db import session_scope
from ..models import Dataset, DatasetResult
from ..storage import load_clean_frame

log = logging.getLogger(__name__)


@dataclass
class EnrichmentContext:
    dataset_id: str
    user_id: str
    df: pd.DataFrame
    analytics: dict
    modules: dict = field(default_factory=dict)
    timings: dict = field(default_factory=dict)


Stage = tuple[str, Callable[[EnrichmentContext], None]]


def get_stages() -> list[Stage]:
    """The ordered stages to run (a function so tests can replace it)."""
    from .stages import DEFAULT_STAGES

    return DEFAULT_STAGES


def _activity(ctx: EnrichmentContext, status: str, accuracy: str, duration: str) -> dict:
    return {
        "id": f"act-{ctx.dataset_id}-ai",
        "task": "AI enrichment (forecast, anomalies, insights)",
        "fileName": ctx.analytics["fileName"],
        "date": datetime.now().strftime("%b %d, %Y, %I:%M %p"),
        "accuracy": accuracy,
        "duration": duration,
        "status": status,
        "recordsCount": ctx.analytics["recordsCount"],
    }


def _set_activity(ctx: EnrichmentContext, act: dict) -> None:
    ctx.analytics["activities"] = [a for a in ctx.analytics["activities"] if a["id"] != act["id"]] + [act]


def run_enrichment(dataset_id: str) -> None:
    """Run all registered stages for a dataset and flip its status to ready/failed."""
    db = session_scope()
    try:
        ds = db.get(Dataset, dataset_id)
        res = db.get(DatasetResult, dataset_id)
        if ds is None or res is None:
            return
        try:
            df = load_clean_frame(ds.user_id, dataset_id)
        except Exception as exc:  # noqa: BLE001
            ds.status, ds.error = "failed", f"Could not load cleaned data: {exc}"
            db.commit()
            return

        ctx = EnrichmentContext(dataset_id, ds.user_id, df, copy.deepcopy(res.analytics), copy.deepcopy(res.modules), dict(res.timings))
        stages = get_stages()
        started = time.perf_counter()
        if stages:
            _set_activity(ctx, _activity(ctx, "Processing", "N/A", "..."))
        for name, fn in stages:
            ds.stage = name
            t0 = time.perf_counter()
            try:
                fn(ctx)
            except Exception as exc:  # noqa: BLE001 - isolation is the point
                log.exception("Stage %s failed for dataset %s", name, dataset_id)
                ctx.modules[name] = {"status": "failed", "reason": str(exc)}
            ctx.timings[name] = round(time.perf_counter() - t0, 2)
            # persist after every stage so the UI's polling shows insights as they arrive
            res.analytics, res.modules, res.timings = copy.deepcopy(ctx.analytics), copy.deepcopy(ctx.modules), dict(ctx.timings)
            db.commit()

        if stages:
            fc = ctx.modules.get("forecast") or {}
            acc = f"{100 - fc['winner_smape']:.1f}%" if fc.get("status") in ("ok", "unreliable") else "N/A"
            _set_activity(ctx, _activity(ctx, "Completed", acc, f"{time.perf_counter() - started:.1f}s"))
        ctx.analytics["status"] = "ready"
        res.analytics, res.modules, res.timings = copy.deepcopy(ctx.analytics), copy.deepcopy(ctx.modules), dict(ctx.timings)
        ds.status, ds.stage = "ready", None
        db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("Enrichment crashed for %s", dataset_id)
        db.rollback()
        ds = db.get(Dataset, dataset_id)
        if ds:
            ds.status, ds.error = "failed", str(exc)
            db.commit()
    finally:
        db.close()
