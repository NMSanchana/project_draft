"""Acceptance tests for scripts/generate_sample_data.py: every module finds its planted pattern."""

import hashlib
import importlib.util

import pytest

from app.llm import ollama_client
from app.pipeline import stages
from app.pipeline.assemble import run_fast_phase
from app.pipeline.enrichment import EnrichmentContext
from tests.conftest import ROOT, SAMPLE_DIR

spec = importlib.util.spec_from_file_location("gen", ROOT / "scripts" / "generate_sample_data.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
GEN = gen.generate(42)
CSV = SAMPLE_DIR / "retail_with_orders.csv"


@pytest.fixture(scope="module")
def ctx():
    ollama_client.is_available = lambda: False
    fr = run_fast_phase(CSV.read_bytes(), "retail_with_orders.csv", "rt")
    c = EnrichmentContext("rt", "u", fr.clean_df, fr.analytics)
    for name, fn in stages.DEFAULT_STAGES[:-2]:  # everything except narrative + Qdrant indexing
        fn(c)
    c.fast = fr
    return c


def test_generator_is_reproducible_and_matches_the_shipped_file():
    again = gen.generate(42)
    h = lambda d: hashlib.sha256(d.to_csv(index=False).encode()).hexdigest()  # noqa: E731
    assert h(GEN) == h(again)
    assert h(GEN) == hashlib.sha256(CSV.read_bytes()).hexdigest(), "sample-data/retail_with_orders.csv is stale: rerun the generator"
    assert list(GEN.columns) == [
        "order_id",
        "date",
        "customer_id",
        "product",
        "category",
        "region",
        "quantity",
        "unit_price",
        "cost",
        "revenue",
        "status",
    ]
    assert len(CSV.read_bytes()) < 10 * 1024 * 1024


def test_fast_phase_kpis_exclude_cancelled_and_returned(ctx):
    ok = GEN[GEN["status"] == "completed"]
    a = ctx.fast.analytics
    assert a["recordsCount"] == len(ok) and a["revenue"] == pytest.approx(round(ok["revenue"].sum(), 2))
    assert a["totalCost"] == pytest.approx(round((ok["cost"] * ok["quantity"]).sum(), 2))  # per-unit cost detected
    assert a["orders"] == ok["order_id"].nunique() and a["uniqueCustomers"] == ok["customer_id"].nunique()
    assert ctx.fast.clean_result.report["status_excluded_rows"] == len(GEN) - len(ok)
    assert len(a["trendData"]) == 8 and a["quality"]["quality_score"] > 90


def test_rules_flag_low_margin_groceries_and_cross_check_titles(ctx):
    titles = [i["title"] for i in ctx.analytics["insights"]]
    assert any(t.startswith("Low Margin Product") and any(p in t for p in ("Coffee", "Tea", "Snacks")) for t in titles)


def test_anomalies_find_planted_spike_and_dip_with_root_cause(ctx):
    res = ctx.modules["anomalies"]
    by = {a["date"]: a for a in res["anomalies"]}
    assert by["2024-02-14"]["direction"] == "spike" and by["2024-03-09"]["direction"] == "dip"
    causes = {c["dimension"]: c["value"] for c in by["2024-02-14"]["causes"]}
    assert causes["region"] == "West" and causes["category"] == "Electronics"
    assert res["count"] <= 5


def test_forecast_beats_seasonal_naive_on_the_seasonal_data(ctx):
    f = ctx.modules["forecast"]
    assert f["status"] in ("ok", "unreliable") and f["beats_seasonal_naive"] and len(f["daily"]) == 30
    assert f["next_30_days"]["lower"] <= f["next_30_days"]["total"] <= f["next_30_days"]["upper"]


def test_drivers_rank_the_south_decline_first(ctx):
    d = ctx.modules["drivers"]
    assert d["current_label"] == "June 2024" and d["change_pct"] < -5 and d["reconciles"]
    assert d["by_dimension"]["region"][0]["value"] == "South" and d["by_dimension"]["region"][0]["delta"] < 0
    assert d["top_segments"][0]["segment"].endswith("-South")


def test_pricing_recovers_planted_elasticities_and_flags_flat_prices(ctx):
    seg = {s["segment"]: s for s in ctx.modules["pricing"]["segments"]}
    assert seg["Groceries"]["reliability"] == "reliable" and seg["Groceries"]["elasticity"] == pytest.approx(-1.8, abs=0.4)
    assert seg["Furniture"]["reliability"] == "reliable" and abs(seg["Furniture"]["elasticity"]) < 1
    assert seg["Electronics"]["reliability"] == "reliable" and seg["Electronics"]["elasticity"] == pytest.approx(-1.1, abs=0.4)
    assert seg["Office"]["reliability"] == "insufficient_evidence" and "barely changes" in seg["Office"]["reason"]


def test_basket_finds_planted_pairs(ctx):
    rules = ctx.modules["basket"]["rules"]
    pairs = {frozenset((r["antecedent"], r["consequent"])) for r in rules[:8]}
    for p in (("Laptop", "Mouse"), ("Desk", "Chair"), ("Monitor", "HDMI Cable")):
        assert frozenset(p) in pairs, pairs


def test_churn_ranks_the_planted_stopping_group_at_the_top(ctx):
    c = ctx.modules["churn"]
    stop = set(GEN.attrs["stopping_customers"])
    assert c["method"] == "model" and c["metrics"]["roc_auc"] > 0.65
    assert sum(t["customer"] in stop for t in c["top_at_risk"]) >= 7
    assert c["lapsed_customers"] >= 30  # the earlier-stopped group is counted as lapsed


def test_segments_cover_all_customers(ctx):
    s = ctx.modules["segments"]
    assert sum(x["revenue_share_pct"] for x in s["segments"]) == pytest.approx(100, abs=0.5) and s["customers"] == 600
