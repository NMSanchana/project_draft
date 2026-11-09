import numpy as np
import pandas as pd
import pytest

from app.ml import basket, drivers, pricing, rfm_churn
from tests.synth_ml import make_baskets, make_customers, make_drivers, make_pricing

CUST = make_customers()


# ======================================================================= Module 1: segments + churn
def test_segments_k_by_silhouette_names_and_revenue_shares():
    s = rfm_churn.run_segments(CUST)
    assert s["status"] == "ok" and 3 <= s["k"] <= 6
    assert str(s["k"]) == max(s["silhouette"], key=s["silhouette"].get)  # k = best silhouette
    names = [x["name"] for x in s["segments"]]
    assert "Champions" in names and len(set(names)) == len(names)
    assert sum(x["revenue_share_pct"] for x in s["segments"]) == pytest.approx(100, abs=0.5)
    assert sum(x["customers"] for x in s["segments"]) == s["customers"]
    champ = next(x for x in s["segments"] if x["name"] == "Champions")
    assert champ["avg_recency_days"] < 30 and champ["top_customers"][0]["monetary"] >= champ["top_customers"][-1]["monetary"]


def test_segments_are_deterministic():
    assert rfm_churn.run_segments(CUST) == rfm_churn.run_segments(CUST)


def test_segments_skip_when_inputs_missing_or_too_few_customers():
    assert "customer column" in rfm_churn.run_segments(CUST.drop(columns="customer"))["reason"]
    few = CUST[CUST["customer"].isin(CUST["customer"].unique()[:10])]
    assert rfm_churn.run_segments(few)["status"] == "skipped"


def test_churn_model_finds_the_group_that_stopped_buying():
    c = rfm_churn.run_churn(CUST)
    assert c["status"] == "ok" and c["method"] == "model"
    assert c["metrics"]["roc_auc"] > 0.8 and {b["model"] for b in c["leaderboard"]} == {"Logistic Regression", "Gradient Boosting"}
    assert c["metrics"]["roc_auc"] == max(b["roc_auc"] for b in c["leaderboard"])
    stopped = sum(1 for t in c["top_at_risk"] if t["customer"].startswith("S"))
    # the planted "S" group is heavily over-represented at the top (regulars / one-off buyers also tie near 100%)
    assert stopped >= 5, c["top_at_risk"]
    assert c["metrics"]["roc_auc"] > 0.9
    assert all(t["churn_probability"] >= 0.5 for t in c["top_at_risk"][:5]) and "leakage_guard" in c
    assert c["at_risk_customers"] >= 50 and 0 < c["at_risk_revenue_share_pct"] <= 100


def test_churn_features_never_use_data_after_the_cutoff():
    p = rfm_churn._purchases(CUST.assign(revenue=CUST["revenue"]))
    cutoff = p["date"].max().normalize() - pd.Timedelta(days=14)
    base = rfm_churn.build_features(p, cutoff, 14)
    tampered = p.copy()
    late = tampered["date"] > cutoff
    tampered.loc[late, "revenue"] *= 1000
    extra = pd.DataFrame(
        {"customer": ["S000", "NEW1"], "date": [cutoff + pd.Timedelta(days=3)] * 2, "_k": ["z1", "z2"], "revenue": [9e9, 9e9]}
    )
    tampered = pd.concat([tampered, extra], ignore_index=True)
    pd.testing.assert_frame_equal(base, rfm_churn.build_features(tampered, cutoff, 14))
    assert "NEW1" not in base.index  # future-only customers are not in the training population
    assert base["recency"].max() <= (cutoff - p["date"].min()).days


def test_churn_heuristic_fallback_is_explicit_when_data_is_small():
    small = CUST[CUST["customer"].isin(sorted(CUST["customer"].unique())[::6])]  # ~60 customers
    c = rfm_churn.run_churn(small)
    assert c["status"] == "ok" and c["method"] == "heuristic" and "heuristic" in c["reason"] and "model" not in c
    assert all(0 <= t["churn_probability"] <= 1 for t in c["top_at_risk"])


def test_churn_skips_with_short_history_or_no_customer():
    assert rfm_churn.run_churn(CUST[CUST["date"] < "2024-01-15"])["status"] == "skipped"
    assert rfm_churn.run_churn(CUST.drop(columns="customer"))["status"] == "skipped"


def test_rfm_insights_text():
    ins = rfm_churn.rfm_insights(rfm_churn.run_segments(CUST), rfm_churn.run_churn(CUST))
    ids = {i["id"] for i in ins}
    assert {"ml-rfm-1", "ml-churn-1"} <= ids
    assert next(i for i in ins if i["id"] == "ml-rfm-1")["title"].startswith("Customer Segments:")
    skipped = rfm_churn.rfm_insights({"status": "skipped", "reason": "No customer column found."}, {"status": "skipped"})
    assert skipped[0]["id"] == "ml-rfm-skipped" and "customer" in skipped[0]["desc"]


# ======================================================================= Module 2: drivers
DRV = make_drivers()


def test_decomposition_sums_exactly_to_total_change():
    r = drivers.run_drivers(DRV)
    assert r["status"] == "ok" and r["reconciles"] and abs(r["reconcile_error"]) < 1e-6
    e = r["effects"]
    assert e["price"] + e["volume"] + e["mix"] == pytest.approx(r["change_abs"], abs=0.05)
    assert r["change_abs"] == pytest.approx(r["revenue_current"] - r["revenue_previous"], abs=0.01)
    assert sum(s["pts"] for s in drivers.run_drivers(DRV)["top_segments"]) <= 100  # sanity


def test_planted_driver_is_ranked_first_and_price_effect_detected():
    r = drivers.run_drivers(DRV)
    assert r["top_segments"][0]["segment"] == "A-West" and r["top_segments"][0]["delta"] < 0
    assert r["effects"]["price"] > 0  # B's +10% price rise
    assert r["by_dimension"]["region"][0]["value"] == "West"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d[~((d.category == "B") & (d.date.dt.month == 1))],  # category B only exists in Feb (new segment)
        lambda d: d[~((d.category == "B") & (d.date.dt.month == 2))],  # category B discontinued in Feb
        lambda d: d.drop(columns=["quantity", "unit_price"]),  # no quantity -> orders as units
        lambda d: d.drop(columns=["category", "region"]),  # no segment columns
    ],
)
def test_decomposition_is_exact_in_edge_cases(mutate):
    r = drivers.run_drivers(mutate(DRV.copy()))
    assert r["status"] == "ok" and r["reconciles"], r.get("reconcile_error")


def test_custom_periods_and_ml_explanation():
    r = drivers.run_drivers(DRV, current=("2024-02-01", "2024-02-29"), previous=("2024-01-01", "2024-01-31"))
    assert r["basis"] == "custom" and r["revenue_current"] < r["revenue_previous"]
    ml = r["ml_explanation"]
    assert ml["status"] == "ok" and ml["model_quality"] in ("good", "poor") and -1 <= ml["holdout_r2"] <= 1
    assert 1 <= len(ml["factors"]) <= 6 and all(f["direction"] in ("up", "down") for f in ml["factors"])
    assert ml["holdout_r2"] > 0.5 and ml["factors"][0]["direction"] == "down"  # the dip is explained as a downward push


def test_drivers_skip_cases_and_insight():
    assert drivers.run_drivers(DRV[DRV.date == DRV.date.min()])["status"] == "skipped"
    ins = drivers.drivers_insights(drivers.run_drivers(DRV))[0]
    assert ins["id"] == "ml-drivers-1" and ins["type"] == "info" and "A-West" in ins["title"] and "fell" in ins["title"]
    assert drivers.drivers_insights({"status": "skipped", "reason": "x"})[0]["id"] == "ml-drivers-skipped"


# ======================================================================= Module 3: pricing
PRC = make_pricing()
PRES = pricing.run_pricing(PRC)
SEG = {s["segment"]: s for s in PRES["segments"]}


def test_elasticity_recovers_planted_values():
    assert PRES["status"] == "ok"
    assert SEG["Inelastic"]["elasticity"] == pytest.approx(-0.5, abs=0.2) and SEG["Inelastic"]["class"] == "inelastic"
    assert SEG["Elastic"]["elasticity"] == pytest.approx(-2.0, abs=0.3) and SEG["Elastic"]["class"] == "elastic"
    for k in ("Inelastic", "Elastic"):
        assert SEG[k]["ci_low"] < SEG[k]["elasticity"] < SEG[k]["ci_high"] and SEG[k]["p_value"] < 0.05


def test_unreliable_segments_are_flagged_not_estimated():
    f = SEG["Fixed"]
    assert f["reliability"] == "insufficient_evidence" and "elasticity" not in f and "barely changes" in f["reason"]
    rng = np.random.default_rng(0)
    noise = PRC[PRC.category == "Elastic"].copy()
    noise["quantity"] = rng.integers(1, 20, len(noise))  # demand unrelated to price
    r = pricing.run_pricing(noise)
    assert r["status"] == "unreliable" and all(s["reliability"] != "reliable" for s in r["segments"])
    tiny = pricing.run_pricing(PRC.head(60))
    assert tiny["status"] == "skipped"


def test_simulator_matches_formula_and_has_ordered_ranges():
    s = pricing.simulate(PRES, "Elastic", 10)
    b = s["elasticity"]
    assert s["reliable"] and s["units_change_pct"] == pytest.approx(100 * (1.1**b - 1), abs=0.05)
    assert s["revenue_delta"] < 0  # elastic: raising price loses revenue
    assert s["revenue_delta_range"][0] <= s["revenue_delta"] <= s["revenue_delta_range"][1]
    assert s["profit_delta_range"][0] <= s["profit_delta"] <= s["profit_delta_range"][1]
    i = pricing.simulate(PRES, "inelastic", 5)  # case-insensitive
    assert i["revenue_delta"] > 0 and i["profit_delta"] > 0


def test_best_move_is_bounded_and_sensible():
    for name in ("Elastic", "Inelastic"):
        bm = SEG[name]["best_move"]
        assert -20 <= bm["price_change_pct"] <= 20 and bm["expected_gain"] >= 0 and bm["optimises"] == "profit"
    assert SEG["Inelastic"]["best_move"]["price_change_pct"] > 0  # inelastic: raise price


def test_simulator_refuses_unreliable_and_out_of_bounds():
    u = pricing.simulate(PRES, "Fixed", 5)
    assert u["reliable"] is False and u["status"] == "unreliable" and "revenue_delta" not in u and "Insufficient evidence" in u["message"]
    with pytest.raises(ValueError):
        pricing.simulate(PRES, "Elastic", 21)
    with pytest.raises(KeyError, match="Elastic"):
        pricing.simulate(PRES, "Nope", 5)


def test_pricing_skips_without_quantity_and_insights():
    assert pricing.run_pricing(PRC.drop(columns=["quantity", "unit_price"]))["status"] == "skipped"
    ins = pricing.pricing_insights(PRES)
    assert ins and ins[0]["id"] == "ml-pricing-1" and "price-" in ins[0]["title"] and "ε" in ins[0]["title"]
    none = pricing.pricing_insights(pricing.run_pricing(PRC[PRC.category == "Fixed"]))
    assert none[0]["id"] == "ml-pricing-skipped"


# ======================================================================= Module 4: basket
def test_planted_pairs_are_the_top_rules():
    r = basket.run_basket(make_baskets())
    assert r["status"] == "ok" and r["basket_basis"] == "order_id" and r["item_level"] == "product"
    top4 = {frozenset((x["antecedent"], x["consequent"])) for x in r["rules"][:4]}
    assert top4 == {frozenset(("Monitor", "HDMI Cable")), frozenset(("Laptop", "Mouse"))}
    for x in r["rules"]:
        assert x["lift"] > 1.2 and x["co_occurrences"] >= 5 and 0 < x["confidence"] <= 1
    assert [x["lift"] for x in r["rules"]] == sorted((x["lift"] for x in r["rules"]), reverse=True)


def test_basket_by_customer_and_date_when_no_order_id():
    b = make_baskets().assign(customer=lambda d: d["order_id"]).drop(columns="order_id")
    r = basket.run_basket(b)
    assert r["status"] == "ok" and r["basket_basis"] == "customer + date" and r["rules"]


def test_single_item_baskets_are_skipped_gracefully():
    one = make_baskets().drop_duplicates("order_id")
    r = basket.run_basket(one)
    assert r["status"] == "skipped" and "one item per order" in r["reason"]
    assert basket.basket_insights(r)[0]["id"] == "ml-basket-skipped"
    assert basket.run_basket(make_baskets().drop(columns="product"))["status"] == "skipped"


def test_basket_insight_text():
    ins = basket.basket_insights(basket.run_basket(make_baskets()))
    assert (
        ins[0]["id"] == "ml-basket-1" and ins[0]["title"].startswith("Cross-sell:") and "lift" in ins[0]["title"] and "→" in ins[0]["title"]
    )


def test_driver_wording_names_contributor_in_direction_of_change():
    # West collapses but East grows even more -> total rises; headline must credit East, and mention West as the offset
    rows = []
    for d in pd.date_range("2024-01-01", "2024-02-29"):
        feb = d.month == 2
        for reg, n in (("West", 4 if feb else 8), ("East", 14 if feb else 6)):
            for _ in range(n):
                rows.append((d, "A", reg, 1, 100.0, 100.0))
    df = pd.DataFrame(rows, columns=["date", "category", "region", "quantity", "unit_price", "revenue"])
    r = drivers.run_drivers(df)
    assert r["change_abs"] > 0 and r["reconciles"]
    assert abs(r["top_segments"][0]["delta"]) >= abs(r["top_segments"][1]["delta"])
    ins = drivers.drivers_insights(r)[0]
    assert "rose" in ins["title"] and "A-East" in ins["title"] and "+" in ins["title"].split("by")[1]
    assert "Partly offset by A-West" in ins["desc"]
