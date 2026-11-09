import pandas as pd

from app.pipeline.kpis import compute_kpis, period_comparison
from app.pipeline.rules import run_rules


def _frame(spec: dict[str, dict[str, tuple[float, float]]], cost_ratio=0.5, customers=1):
    """spec[region][category] = (prev_month_revenue, cur_month_revenue); months Jan & Feb 2024 (full)."""
    rows = []
    for region, cats in spec.items():
        for cat, (prev, cur) in cats.items():
            for month_start, rev in (("2024-01-01", prev), ("2024-02-01", cur)):
                for day in (0, 14, 28):  # three orders each, spanning the month incl. edges
                    rows.append(
                        {
                            "date": pd.Timestamp(month_start) + pd.Timedelta(days=day),
                            "region": region,
                            "category": cat,
                            "revenue": rev / 3,
                            "cost": rev / 3 * cost_ratio,
                            "customer": f"C{len(rows) % customers}",
                            "order_id": f"O{len(rows)}",
                        }
                    )
    df = pd.DataFrame(rows)
    df.loc[df["date"].dt.month == 1, "date"] = df["date"].where(df["date"].dt.month == 1).apply(lambda d: d if d.day <= 31 else d)
    return df


def _run(df):
    k = compute_kpis(df)
    return run_rules(df, k, period_comparison(df)), k


def ids(ins):
    return {i["id"] for i in ins}


def test_strong_growth_fires_above_10_percent_and_not_below():
    up, _ = _run(_frame({"N": {"A": (1000, 1150)}}))  # +15%
    flat, _ = _run(_frame({"N": {"A": (1000, 1080)}}))  # +8%
    assert "strong-growth" in ids(up) and "strong-growth" not in ids(flat)
    sg = next(i for i in up if i["id"] == "strong-growth")
    assert (sg["type"], sg["severity"]) == ("growth", "Low") and "15.0%" in sg["title"]


def test_revenue_decline_below_minus_10():
    ins, _ = _run(_frame({"N": {"A": (1000, 850)}}))
    d = next(i for i in ins if i["id"] == "revenue-decline")
    assert (d["type"], d["severity"]) == ("alert", "High")
    assert "revenue-decline" not in ids(_run(_frame({"N": {"A": (1000, 920)}}))[0])


def test_declining_product_below_minus_15_and_region_growth_above_20():
    # categories: A -20% (declining), B flat, C +60%; region S grows 1000 -> 1300 (+30%)
    df = _frame({"N": {"A": (1000, 800), "B": (1000, 1000)}, "S": {"C": (500, 800), "B": (500, 500)}})
    ins, _ = _run(df)
    assert any(i["id"].startswith("declining-product") and "A down 20.0%" in i["title"] for i in ins)
    assert not any("B down" in i["title"] for i in ins)
    r = next(i for i in ins if i["id"].startswith("regional-opportunity"))
    assert r["type"] == "opportunity" and r["severity"] == "Medium" and "S up 30.0%" in r["title"]
    # just under the thresholds: category -14%, region +18% -> neither fires
    quiet, _ = _run(_frame({"N": {"A": (1000, 860)}, "S": {"B": (500, 590)}}))
    assert not any(i["id"].startswith(("declining-product", "regional-opportunity")) for i in quiet)


def test_low_margin_threshold_15_percent():
    low, k = _run(_frame({"N": {"A": (1000, 1000)}}, cost_ratio=0.9))  # margin 10%
    ok, _ = _run(_frame({"N": {"A": (1000, 1000)}}, cost_ratio=0.8))  # margin 20%
    assert "low-margin" in ids(low) and "low-margin" not in ids(ok)
    assert any(i["id"].startswith("low-margin-category") for i in low)


def test_no_margin_rules_without_cost():
    df = _frame({"N": {"A": (1000, 1000)}}).drop(columns=["cost"])
    ins, _ = _run(df)
    assert not any(i["id"].startswith("low-margin") for i in ins)


def test_high_value_customer_top_10_percent():
    rows = [
        {
            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i % 60),
            "revenue": 1000.0 if c == 0 else 10.0,
            "customer": f"C{c}",
            "cost": 5.0,
        }
        for i, c in enumerate(range(20))
    ]
    df = pd.DataFrame(rows)
    ins, _ = _run(df)
    h = next(i for i in ins if i["id"] == "high-value-customer")
    assert h["severity"] == "Info" and "top 2 customers" in h["title"] and "C0" in h["desc"]


def test_all_insights_match_frontend_contract():
    ins, _ = _run(_frame({"N": {"A": (1000, 800)}, "S": {"A": (500, 700)}}, cost_ratio=0.9, customers=20))
    for i in ins:
        assert set(i) == {"id", "type", "severity", "title", "desc", "recommendation"}
        assert i["type"] in {"growth", "alert", "opportunity", "info"} and i["severity"] in {"High", "Medium", "Low", "Info"}
