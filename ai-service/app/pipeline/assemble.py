"""Fast phase: turn a cleaned frame into the frontend's ``ProcessedAnalytics`` object."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from ..schemas import ProcessedAnalytics
from .clean import CleanResult, clean
from .ingest import read_csv_bytes
from .kpis import compute_kpis, period_comparison
from .roles import detect_roles
from .rules import run_rules
from .trend import build_trend


@dataclass
class FastResult:
    analytics: dict  # JSON-ready ProcessedAnalytics (+extras)
    clean_df: pd.DataFrame
    clean_result: CleanResult
    kpis: dict
    seconds: float


def _data_quality_insights(cr: CleanResult, kpis: dict) -> list[dict]:
    """Honest ``info`` insights about what the data could and could not support."""
    out: list[dict] = []
    if not kpis["has_cost"]:
        out.append(
            {
                "id": "data-no-cost",
                "type": "info",
                "severity": "Info",
                "title": "Data Quality: No cost or profit data found",
                "desc": "The file has no cost or profit column, so profit and margin are shown as 0 and margin-based insights are skipped.",
                "recommendation": "Add a 'cost' (or 'profit') column to unlock margin analysis and pricing advice.",
            }
        )
    low = {r: c for r, c in cr.roles.confidence.items() if c < 0.6}
    if low:
        txt = ", ".join(f"{r} -> '{cr.roles.roles[r]}'" for r in low)
        out.append(
            {
                "id": "data-low-confidence-roles",
                "type": "info",
                "severity": "Info",
                "title": "Data Quality: Some columns were guessed",
                "desc": f"Low-confidence column mapping: {txt}.",
                "recommendation": "Rename these columns to common names (e.g. 'revenue', 'order_date') for more reliable results.",
            }
        )
    if cr.report.get("cost_basis") == "per_unit":
        out.append(
            {
                "id": "data-cost-per-unit",
                "type": "info",
                "severity": "Info",
                "title": "Data Quality: Cost is per unit",
                "desc": f"Column '{cr.roles.roles['cost']}' looks like a per-unit cost, so it was multiplied by quantity to compute total cost and margin.",
                "recommendation": "If this column is already a line total, rename it to 'total_cost' to avoid the conversion.",
            }
        )
    rep = cr.report
    removed = rep["duplicates_removed"] + rep["negative_rows_removed"] + rep["invalid_dates_removed"] + rep["status_excluded_rows"]
    if removed:
        out.append(
            {
                "id": "data-rows-removed",
                "type": "info",
                "severity": "Low",
                "title": f"Data Quality: {removed} rows removed during cleaning",
                "desc": (
                    f"{rep['duplicates_removed']} duplicates, {rep['negative_rows_removed']} rows with negative values, "
                    f"{rep['invalid_dates_removed']} rows with unreadable dates and {rep['status_excluded_rows']} cancelled/returned "
                    "orders (status column) were removed."
                ),
                "recommendation": "Check the source export if these counts look unexpected.",
            }
        )
    return out


def run_fast_phase(raw: bytes, file_name: str, dataset_id: str | None = None) -> FastResult:
    """Ingest -> detect roles -> clean -> KPIs -> trend -> ProcessedAnalytics. Raises DataError on bad data."""
    t0 = time.perf_counter()
    ing = read_csv_bytes(raw)
    det = detect_roles(ing.df)
    cr = clean(ing.df, det)
    cr.report["encoding"], cr.report["delimiter"] = ing.encoding, ing.delimiter
    cr.report["notes"] = ing.warnings + cr.report["notes"]
    kpis = compute_kpis(cr.df)
    pc = kpis["period_change"]
    trend = build_trend(cr.df, pc["change_pct"] if pc and pc["basis"] == "month" else None)
    seconds = time.perf_counter() - t0

    analytics = ProcessedAnalytics(
        fileName=file_name,
        recordsCount=kpis["rows"],
        revenue=kpis["revenue"],
        totalCost=kpis["total_cost"],
        totalProfit=kpis["total_profit"],
        profitMargin=kpis["profit_margin_pct"],
        orders=kpis["orders"],
        uniqueCustomers=kpis["unique_customers"],
        trendData=trend["trendData"],
        trendSummary=trend["trendSummary"],
        trendBadge=trend["trendBadge"],
        insights=run_rules(cr.df, kpis, period_comparison(cr.df)) + _data_quality_insights(cr, kpis),
        activities=[
            {
                "id": f"act-{dataset_id or 'x'}-ingest",
                "task": "Data ingestion & cleaning",
                "fileName": file_name,
                "date": datetime.now().strftime("%b %d, %Y, %I:%M %p"),
                "accuracy": f"{cr.report['quality_score']:.1f}%",
                "duration": f"{seconds:.1f}s",
                "status": "Completed",
                "recordsCount": kpis["rows"],
            }
        ],
        datasetId=dataset_id,
        status="enriching",
        quality=cr.report,
        kpis={k: v for k, v in kpis.items() if k != "period_change"} | {"period_change": pc},
    ).model_dump(exclude_none=True)
    analytics["trendGranularity"] = trend["granularity"]
    return FastResult(analytics=analytics, clean_df=cr.df, clean_result=cr, kpis=kpis, seconds=seconds)
