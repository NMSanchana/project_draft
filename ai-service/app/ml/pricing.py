"""ML Module 3: price elasticity and the what-if pricing simulator.

Plain idea: learn how customers react when price moves, then answer "what if I raise this by 5%?".

Model (per segment, plus a pooled "All" row)
    ln(quantity) = a + b * ln(price) + product dummies + month dummies + region dummies    (statsmodels OLS, HC1 robust errors)
Product dummies (when a product column exists) make ``b`` a *within-product* effect: a cheap and an expensive
product in the same category are not confused with a price change of one product.
``b`` is the price elasticity: -0.6 means a +10% price lowers units by about 6%.

Reliability (never a made-up number)
  * fewer than 100 rows                           -> ``insufficient_evidence``
  * std(ln price) < 0.05 (price barely varies)    -> ``insufficient_evidence``
  * p-value >= 0.05                               -> ``insufficient_evidence``
  * positive elasticity (almost surely confounded)-> ``implausible``
Only ``reliable`` segments produce simulator numbers.

Simulator: units' = Q * (1+d)^b, revenue' = P(1+d) * units', profit' = (P(1+d) - unit_cost) * units'.
The range comes from the elasticity's 95% confidence interval. Changes are limited to +-20%.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

MIN_ROWS = 100
MIN_PRICE_SD = 0.05
MAX_CHANGE_PCT = 20.0
BASELINE_DAYS = 30
MAX_PRODUCT_SEGMENTS = 50


def _design(sub: pd.DataFrame, extra_dummies: list[str]) -> pd.DataFrame:
    X = pd.DataFrame({"lnp": np.log(sub["unit_price"])}, index=sub.index)
    months = sub["date"].dt.to_period("M").astype(str)
    cols = [months.rename("month")]
    if "region" in sub:
        cols.append(sub["region"].rename("region"))
    for d in extra_dummies:
        cols.append(sub[d].rename(f"seg_{d}"))
    for c in cols:
        if c.nunique() > 1:
            X = X.join(pd.get_dummies(c, prefix=c.name, drop_first=True, dtype=float))
    return sm.add_constant(X, has_constant="add")


def _within_sd(sub: pd.DataFrame, groups: list[str]) -> float:
    """Std of ln(price) after removing each group's mean, so between-product price gaps do not count as 'variation'."""
    lp = np.log(sub["unit_price"])
    if groups and groups[0] in sub:
        lp = lp - lp.groupby(sub[groups[0]]).transform("mean")
    return float(lp.std()) if len(lp) > 1 else 0.0


def _fit_one(sub: pd.DataFrame, extra_dummies: list[str] | None = None) -> dict:
    n = int(len(sub))
    sd = _within_sd(sub, extra_dummies or [])
    base = {"n": n, "price_sd": round(sd, 4)}
    if n < MIN_ROWS:
        return {**base, "reliability": "insufficient_evidence", "reason": f"Only {n} sales rows (need {MIN_ROWS})."}
    if sd < MIN_PRICE_SD:
        return {
            **base,
            "reliability": "insufficient_evidence",
            "reason": "Price barely changes in this data, so its effect on demand cannot be measured.",
        }
    try:
        X = _design(sub, extra_dummies or [])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = sm.OLS(np.log(sub["quantity"]), X).fit(cov_type="HC1")
        b, p = float(res.params["lnp"]), float(res.pvalues["lnp"])
        lo, hi = (float(v) for v in res.conf_int().loc["lnp"])
    except Exception as exc:  # noqa: BLE001 - singular designs etc.
        return {**base, "reliability": "insufficient_evidence", "reason": f"Model could not be fitted ({str(exc)[:60]})."}
    out = {
        **base,
        "elasticity": round(b, 3),
        "ci_low": round(lo, 3),
        "ci_high": round(hi, 3),
        "p_value": round(p, 4),
        "r2": round(float(res.rsquared), 3),
    }
    if not np.isfinite(b) or not np.isfinite(p) or p >= 0.05:
        return {
            **out,
            "reliability": "insufficient_evidence",
            "reason": f"The price effect is not statistically significant (p = {p:.2f}).",
        }
    if b > 0:
        return {
            **out,
            "reliability": "implausible",
            "reason": "Estimated elasticity is positive (higher price, higher sales), which usually means confounding.",
        }
    return {**out, "reliability": "reliable", "class": "inelastic" if abs(b) < 1 else ("elastic" if abs(b) > 1 else "unit-elastic")}


def _baseline(sub: pd.DataFrame) -> dict:
    recent = sub[sub["date"] > sub["date"].max() - pd.Timedelta(days=BASELINE_DAYS)]
    b = recent if len(recent) >= 10 else sub
    units, rev = float(b["quantity"].sum()), float(b["revenue"].sum())
    cost = float(b["cost"].sum()) if "cost" in b else None
    return {
        "window": f"last {BASELINE_DAYS} days" if b is recent else "all data",
        "units": round(units, 2),
        "avg_price": round(rev / units, 4),
        "revenue": round(rev, 2),
        "unit_cost": None if cost is None else round(cost / units, 4),
        "profit": None if cost is None else round(rev - cost, 2),
    }


def _outcome(base: dict, b: float, pct: float) -> dict:
    f = 1 + pct / 100
    units = base["units"] * f**b
    rev = base["avg_price"] * f * units
    profit = None if base["unit_cost"] is None else (base["avg_price"] * f - base["unit_cost"]) * units
    return {"units": units, "revenue": rev, "profit": profit}


def _best_move(base: dict, b: float) -> dict:
    key = "profit" if base["unit_cost"] is not None else "revenue"
    grid = np.arange(-MAX_CHANGE_PCT, MAX_CHANGE_PCT + 0.5, 1.0)
    vals = [_outcome(base, b, float(g))[key] for g in grid]
    i = int(np.argmax(vals))
    cur = base["profit"] if key == "profit" else base["revenue"]
    return {"price_change_pct": float(grid[i]), "optimises": key, "expected_gain": round(float(vals[i] - cur), 2)}


def run_pricing(df: pd.DataFrame) -> dict:
    if "quantity" not in df or "unit_price" not in df:
        return {"status": "skipped", "reason": "Pricing analysis needs quantity and price (or revenue and quantity) columns."}
    d = df[(df["quantity"] > 0) & (df["unit_price"] > 0)]
    if len(d) < MIN_ROWS:
        return {"status": "skipped", "reason": f"Need at least {MIN_ROWS} sales rows with price and quantity (found {len(d)})."}

    seg_col = "category" if "category" in d else ("product" if "product" in d and d["product"].nunique() <= MAX_PRODUCT_SEGMENTS else None)
    entries = []
    has_product = "product" in d and 1 < d["product"].nunique() <= 200
    fe = ["product"] if has_product else ([seg_col] if seg_col and d[seg_col].nunique() > 1 else [])
    entries.append({"segment": "All", **_fit_one(d, fe), "baseline": _baseline(d)})
    if seg_col:
        for name, sub in d.groupby(seg_col):
            sub_fe = ["product"] if has_product and sub["product"].nunique() > 1 else []
            entries.append({"segment": str(name), **_fit_one(sub, sub_fe), "baseline": _baseline(sub)})
    for e in entries:
        if e["reliability"] == "reliable":
            e["best_move"] = _best_move(e["baseline"], e["elasticity"])
    reliable = [e for e in entries if e["reliability"] == "reliable"]
    res = {
        "status": "ok" if reliable else "unreliable",
        "method": "log-log OLS with month/region controls (HC1)",
        "segment_dimension": seg_col or "(none)",
        "max_change_pct": MAX_CHANGE_PCT,
        "segments": entries,
    }
    if not reliable:
        res["reason"] = "No segment shows a statistically reliable price effect (insufficient price variation or evidence)."
    return res


def simulate(result: dict, segment: str, price_change_pct: float) -> dict:
    """Predict the effect of a price change. Raises KeyError (unknown segment) or ValueError (out of bounds)."""
    if abs(price_change_pct) > MAX_CHANGE_PCT:
        raise ValueError(f"priceChangePct must be within +-{MAX_CHANGE_PCT:.0f}%.")
    seg = next((s for s in result.get("segments", []) if s["segment"].lower() == segment.strip().lower()), None)
    if seg is None:
        raise KeyError(", ".join(s["segment"] for s in result.get("segments", [])))
    head = {"segment": seg["segment"], "price_change_pct": price_change_pct, "reliability": seg["reliability"]}
    if seg["reliability"] != "reliable":
        return {**head, "status": "unreliable", "reliable": False, "message": f"Insufficient evidence to predict this: {seg['reason']}"}
    base, b = seg["baseline"], seg["elasticity"]
    point = _outcome(base, b, price_change_pct)
    ends = [_outcome(base, e, price_change_pct) for e in (seg["ci_low"], b, seg["ci_high"])]

    def delta(o, k, ref):
        return None if o[k] is None or ref is None else float(o[k] - ref)

    rng = lambda k, ref: (
        None
        if ref is None
        else [
            round(min(delta(o, k, ref) for o in ends), 2),  # noqa: E731
            round(max(delta(o, k, ref) for o in ends), 2),
        ]
    )
    return {
        **head,
        "status": "ok",
        "reliable": True,
        "elasticity": b,
        "elasticity_ci": [seg["ci_low"], seg["ci_high"]],
        "baseline": base,
        "units_change_pct": round(100 * (point["units"] / base["units"] - 1), 2),
        "revenue_delta": round(delta(point, "revenue", base["revenue"]), 2),
        "revenue_delta_range": rng("revenue", base["revenue"]),
        "profit_delta": None if base["profit"] is None else round(delta(point, "profit", base["profit"]), 2),
        "profit_delta_range": rng("profit", base["profit"]),
        "recommended": seg.get("best_move"),
        "note": "Estimate based on observed price variation; range uses the 95% confidence interval of the elasticity.",
    }


def pricing_insights(res: dict, limit: int = 3) -> list[dict]:
    if res["status"] == "skipped":
        return [
            {
                "id": "ml-pricing-skipped",
                "type": "info",
                "severity": "Info",
                "title": "Pricing: not available",
                "desc": res["reason"],
                "recommendation": "Include quantity and price (or revenue and quantity) columns.",
            }
        ]
    rel = sorted(
        (e for e in res["segments"] if e["reliability"] == "reliable" and e["segment"] != "All"), key=lambda e: -e["baseline"]["revenue"]
    ) or [e for e in res["segments"] if e["reliability"] == "reliable"]
    if not rel:
        return [
            {
                "id": "ml-pricing-skipped",
                "type": "info",
                "severity": "Info",
                "title": "Pricing: insufficient evidence to estimate price sensitivity",
                "desc": res.get("reason", "Price barely varies in this data."),
                "recommendation": "Vary prices in small tests (or include more price history) to measure elasticity.",
            }
        ]
    out = []
    for i, e in enumerate(rel[:limit], 1):
        inelastic = abs(e["elasticity"]) < 1
        step = 5.0 if inelastic else -5.0
        sim = simulate(res, e["segment"], step)
        gain = sim["profit_delta"] if sim["profit_delta"] is not None else sim["revenue_delta"]
        rng = sim["profit_delta_range"] if sim["profit_delta"] is not None else sim["revenue_delta_range"]
        what = "profit" if sim["profit_delta"] is not None else "revenue"
        name = "overall demand" if e["segment"] == "All" else e["segment"]
        bm = e["best_move"]
        out.append(
            {
                "id": f"ml-pricing-{i}",
                "type": "opportunity" if gain > 0 else "info",
                "severity": "Medium" if gain > 0 else "Info",
                "title": f"Pricing: {name} is price-{'inelastic' if inelastic else 'elastic'} (ε = {e['elasticity']:.1f})",
                "desc": (
                    f"A {step:+.0f}% price change is predicted to change {what} by about ${gain:,.0f} "
                    f"(range ${rng[0]:,.0f} to ${rng[1]:,.0f}). The {what}-maximising move within ±20% is {bm['price_change_pct']:+.0f}%."
                ),
                "recommendation": (
                    f"Trial a small {'increase' if step > 0 else 'cut'} on {name} and watch volumes; "
                    "do not exceed ±20% without more data."
                ),
            }
        )
    return out
