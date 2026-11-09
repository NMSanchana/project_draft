"""Enrichment stages (phase 2). Each stage mutates the :class:`EnrichmentContext`."""

from __future__ import annotations

from ..ml.basket import basket_insights, run_basket
from ..ml.drivers import drivers_insights, run_drivers
from ..ml.pricing import pricing_insights, run_pricing
from ..ml.rfm_churn import rfm_insights, run_churn, run_segments
from ..rag import facts as rag_facts
from ..rag import store as rag_store
from ..rag.embeddings import EmbedderUnavailable
from .anomalies import anomaly_insights, run_anomalies
from .enrichment import EnrichmentContext
from .forecast import forecast_insight, run_forecast
from .narrative import build_facts, make_narrative


def add_insights(ctx: EnrichmentContext, items: list[dict]) -> None:
    have = {str(i["id"]) for i in ctx.analytics["insights"]}
    ctx.analytics["insights"].extend(i for i in items if str(i["id"]) not in have)


def _skipped_info(module: str, title: str, reason: str) -> dict:
    return {
        "id": f"ml-{module}-skipped",
        "type": "info",
        "severity": "Info",
        "title": title,
        "desc": reason,
        "recommendation": "Upload a longer history (at least 4 weeks of daily data).",
    }


def stage_forecast(ctx: EnrichmentContext) -> None:
    res = run_forecast(ctx.df)
    ctx.modules["forecast"] = res
    ml = ctx.analytics.setdefault("ml", {})
    if res["status"] == "skipped":
        ml["forecast"] = {"status": "skipped", "reason": res["reason"]}
        add_insights(ctx, [_skipped_info("forecast", "Forecast: not enough history", res["reason"])])
        return
    ml["forecast"] = {
        "status": res["status"],
        "winner": res["winner"],
        "smape": res["winner_smape"],
        "next_30_days": res["next_30_days"],
        "beats_seasonal_naive": res["beats_seasonal_naive"],
    }
    add_insights(ctx, [forecast_insight(res)])


def stage_anomalies(ctx: EnrichmentContext) -> None:
    res = run_anomalies(ctx.df)
    ctx.modules["anomalies"] = res
    ml = ctx.analytics.setdefault("ml", {})
    if res["status"] == "skipped":
        ml["anomalies"] = {"status": "skipped", "reason": res["reason"]}
        add_insights(ctx, [_skipped_info("anomalies", "Anomalies: not enough history", res["reason"])])
        return
    ml["anomalies"] = {"status": "ok", "count": res["count"]}
    add_insights(ctx, anomaly_insights(res))


def stage_narrative(ctx: EnrichmentContext) -> None:
    facts = build_facts(ctx.df, ctx.analytics, ctx.modules)
    res = make_narrative(facts)
    prefix, tag = ("llm", "AI Insight: ") if res["source"] == "llm" else ("tpl", "")
    items = [{"id": f"{prefix}-{i}", "severity": "Info", **{**it, "title": tag + it["title"]}} for i, it in enumerate(res["insights"], 1)]
    add_insights(ctx, items)
    ctx.modules["narrative"] = {k: v for k, v in res.items() if k != "insights"} | {"facts": facts}


def _summary(res: dict, *keys: str) -> dict:
    out = {"status": res["status"]}
    if res["status"] == "skipped":
        out["reason"] = res["reason"]
    else:
        out.update({k: res[k] for k in keys if k in res})
    return out


def stage_rfm_churn(ctx: EnrichmentContext) -> None:
    seg = run_segments(ctx.df)
    churn = run_churn(ctx.df) if seg["status"] != "skipped" else {"status": "skipped", "reason": seg["reason"]}
    ctx.modules["segments"], ctx.modules["churn"] = seg, churn
    ml = ctx.analytics.setdefault("ml", {})
    ml["segments"] = _summary(seg, "k", "customers") | (
        {}
        if seg["status"] == "skipped"
        else {
            "segments": [
                {"name": x["name"], "customers": x["customers"], "revenue_share_pct": x["revenue_share_pct"]} for x in seg["segments"]
            ]
        }
    )
    ml["churn"] = _summary(churn, "method", "model", "at_risk_customers", "at_risk_revenue_share_pct", "window_days")
    add_insights(ctx, rfm_insights(seg, churn))


def stage_drivers(ctx: EnrichmentContext) -> None:
    res = run_drivers(ctx.df)
    ctx.modules["drivers"] = res
    ctx.analytics.setdefault("ml", {})["drivers"] = _summary(res, "current_label", "previous_label", "change_pct", "effects", "reconciles")
    add_insights(ctx, drivers_insights(res))


def stage_pricing(ctx: EnrichmentContext) -> None:
    res = run_pricing(ctx.df)
    ctx.modules["pricing"] = res
    rel = (
        []
        if res["status"] == "skipped"
        else [{"segment": e["segment"], "elasticity": e["elasticity"]} for e in res["segments"] if e["reliability"] == "reliable"]
    )
    ctx.analytics.setdefault("ml", {})["pricing"] = _summary(res) | ({"reliable_segments": rel} if rel else {})
    add_insights(ctx, pricing_insights(res))


def stage_basket(ctx: EnrichmentContext) -> None:
    res = run_basket(ctx.df)
    ctx.modules["basket"] = res
    ctx.analytics.setdefault("ml", {})["basket"] = _summary(res, "baskets", "multi_item_baskets") | (
        {"top_rule": res["rules"][0]} if res.get("rules") else {}
    )
    add_insights(ctx, basket_insights(res))


def stage_index(ctx: EnrichmentContext) -> None:
    """Index the dataset's own facts in Qdrant so chat can retrieve explanations. Skipped if Qdrant is down."""
    try:
        rag_store.ping()
    except rag_store.VectorStoreUnavailable as exc:
        ctx.modules["index"] = {"status": "skipped", "reason": str(exc)}
        return
    try:
        n = rag_facts.index_dataset(ctx.dataset_id, ctx.df, ctx.analytics, ctx.modules)
    except EmbedderUnavailable as exc:
        ctx.modules["index"] = {"status": "skipped", "reason": str(exc)}
        return
    ctx.modules["index"] = {"status": "ok", "facts": n}


DEFAULT_STAGES = [
    ("forecast", stage_forecast),
    ("anomalies", stage_anomalies),
    ("rfm_churn", stage_rfm_churn),
    ("drivers", stage_drivers),
    ("pricing", stage_pricing),
    ("basket", stage_basket),
    ("narrative", stage_narrative),
    ("index", stage_index),
]
