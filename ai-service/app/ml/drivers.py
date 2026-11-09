"""ML Module 2: "Why did revenue change?" (explainable AI).

Plain idea: a detective's report naming exactly what caused the rise or dip.

Layer A, exact decomposition (the ground truth)
  Per segment s (category x region when available), with q = units, p = average price:
      volume_s = (Q1/Q0 - 1) * q0_s * p0_s            (the whole business grew/shrank)
      mix_s    = (q1_s - q0_s * Q1/Q0) * p0_s         (segment gained/lost share of units)
      price_s  = (p1_s - p0_s) * q1_s                 (same units sold at a different price)
  volume_s + mix_s + price_s = R1_s - R0_s **exactly**, so the effects sum to the total change.
  New segments use p0 = p1 and discontinued ones p1 = p0 (so they are pure mix/volume).
  Without a quantity column each order line counts as one unit (price effect then measures
  order-value changes).

Layer B, ML explanation
  HistGradientBoostingRegressor predicts *daily* revenue from calendar features, category/region
  mix shares, average price and units. SHAP TreeExplainer attributes predictions to features; the
  mean SHAP difference between the target and baseline days ranks which factors pushed revenue.
  The hold-out R^2 is reported; when it is poor, Layer A alone should be trusted.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score

from ..pipeline.kpis import period_comparison

SEED = 42
MIN_DAYS_ML = 21
POOR_R2 = 0.5


def _range_label(rng: tuple[str, str]) -> str:
    """'February 2024' when the range is exactly one calendar month, else 'start to end'."""
    a, b = pd.Timestamp(rng[0]), pd.Timestamp(rng[1])
    if a.day == 1 and a.to_period("M") == b.to_period("M") and b.normalize() == b.to_period("M").end_time.normalize():
        return a.strftime("%B %Y")
    return f"{rng[0]} to {rng[1]}"


def _periods(df: pd.DataFrame, current: tuple[str, str] | None, previous: tuple[str, str] | None) -> dict | None:
    if current and previous:

        def mask(rng):
            return (df["date"] >= pd.Timestamp(rng[0])) & (df["date"] < pd.Timestamp(rng[1]) + pd.Timedelta(days=1))

        cm, pm = mask(current), mask(previous)
        return {
            "current_mask": cm,
            "previous_mask": pm,
            "basis": "custom",
            "current_label": _range_label(current),
            "previous_label": _range_label(previous),
        }
    return period_comparison(df)


def _segment_dims(df: pd.DataFrame) -> list[str]:
    dims = [d for d in ("category", "region") if d in df]
    if not dims and "product" in df:
        dims = ["product"]
    return dims


def decompose(cur: pd.DataFrame, prev: pd.DataFrame, dims: list[str]) -> pd.DataFrame:
    """Exact price / volume / mix decomposition per segment (see module docstring)."""

    def agg(d: pd.DataFrame) -> pd.DataFrame:
        units = d["quantity"] if "quantity" in d else pd.Series(1.0, index=d.index)
        t = d.assign(_q=units)
        if dims:
            g = t.groupby(dims, observed=True).agg(R=("revenue", "sum"), q=("_q", "sum"))
        else:
            g = pd.DataFrame({"R": [t["revenue"].sum()], "q": [t["_q"].sum()]}, index=["All"])
        return g

    a0, a1 = agg(prev), agg(cur)
    t = a0.join(a1, how="outer", lsuffix="0", rsuffix="1").fillna(0.0)
    Q0, Q1 = float(t["q0"].sum()), float(t["q1"].sum())
    p0 = np.where(t["q0"] > 0, t["R0"] / t["q0"].replace(0, np.nan), np.nan)
    p1 = np.where(t["q1"] > 0, t["R1"] / t["q1"].replace(0, np.nan), np.nan)
    p0, p1 = np.where(np.isnan(p0), p1, p0), np.where(np.isnan(p1), p0, p1)
    ratio = Q1 / Q0
    t["volume"] = (ratio - 1) * t["q0"] * p0
    t["mix"] = (t["q1"] - t["q0"] * ratio) * p0
    t["price"] = (p1 - p0) * t["q1"]
    t["delta"] = t["R1"] - t["R0"]
    return t


def _label(idx) -> str:
    return "-".join(str(x) for x in idx) if isinstance(idx, tuple) else str(idx)


def _ml_explain(df: pd.DataFrame, pm: dict) -> dict:
    """Layer B. Returns a dict with ``status`` and, when ok, ranked SHAP factors."""
    with warnings.catch_warnings():  # shap/matplotlib print noisy deprecation warnings on import
        warnings.simplefilter("ignore")
        import shap

    day = df["date"].dt.normalize()
    units = df["quantity"] if "quantity" in df else pd.Series(1.0, index=df.index)
    daily = pd.DataFrame({"revenue": df.groupby(day)["revenue"].sum(), "units": units.groupby(day).sum()})
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D"), fill_value=0.0)
    if len(daily) < MIN_DAYS_ML:
        return {"status": "skipped", "reason": f"Need at least {MIN_DAYS_ML} days for the ML explanation (found {len(daily)})."}
    daily["avg_price"] = (daily["revenue"] / daily["units"].replace(0, np.nan)).fillna(0.0)
    daily["dow"], daily["dom"] = daily.index.dayofweek, daily.index.day
    daily["weekend"] = (daily["dow"] >= 5).astype(int)
    labels = {"dow": "day of week", "dom": "day of month", "weekend": "weekend", "units": "units sold", "avg_price": "average price"}
    for dim in ("category", "region"):
        if dim in df:
            top = df.groupby(dim)["revenue"].sum().nlargest(4).index
            share = df.assign(_d=day).pivot_table(index="_d", columns=dim, values="revenue", aggfunc="sum", fill_value=0.0)
            share = share.div(share.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).reindex(daily.index, fill_value=0.0)
            for v in top:
                name = f"share_{dim}:{v}"
                daily[name] = share[v]
                labels[name] = f"{v} share of daily revenue ({dim})"
    feats = [c for c in daily.columns if c != "revenue"]
    X, y = daily[feats], daily["revenue"]

    split = int(len(daily) * 0.8)
    hgb = lambda: HistGradientBoostingRegressor(
        max_iter=200,
        learning_rate=0.05,
        max_depth=3,  # noqa: E731
        min_samples_leaf=3,
        random_state=SEED,
    )
    r2 = float(r2_score(y.iloc[split:], hgb().fit(X.iloc[:split], y.iloc[:split]).predict(X.iloc[split:])))
    model = hgb().fit(X, y)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sv = shap.TreeExplainer(model).shap_values(X)
    sv = pd.DataFrame(np.asarray(sv), index=daily.index, columns=feats)

    cur_days = set(day[pm["current_mask"]])
    prev_days = set(day[pm["previous_mask"]])
    ci, pi = sv.index.isin(cur_days), sv.index.isin(prev_days)
    delta = sv[ci].mean() - sv[pi].mean()
    pred_gap = float(model.predict(X[ci]).mean() - model.predict(X[pi]).mean())
    ranked = delta.reindex(delta.abs().sort_values(ascending=False).index)
    factors = [
        {"feature": f, "label": labels.get(f, f), "effect_per_day": round(float(v), 2), "direction": "up" if v > 0 else "down"}
        for f, v in ranked.head(6).items()
    ]
    quality = "good" if r2 >= POOR_R2 else "poor"
    out = {
        "status": "ok",
        "model": "HistGradientBoostingRegressor + SHAP TreeExplainer",
        "holdout_r2": round(r2, 3),
        "model_quality": quality,
        "days_used": int(len(daily)),
        "predicted_daily_revenue_gap": round(pred_gap, 2),
        "factors": factors,
    }
    if quality == "poor":
        out["note"] = f"Hold-out R^2 is only {r2:.2f}; rely on the exact decomposition, not the SHAP ranking."
    return out


def run_drivers(df: pd.DataFrame, current: tuple[str, str] | None = None, previous: tuple[str, str] | None = None) -> dict:
    """Explain the revenue change between two periods (default: last full month vs the one before)."""
    pm = _periods(df, current, previous)
    if pm is None:
        return {"status": "skipped", "reason": "Need at least two periods of data (more than one day) to compare."}
    cur, prev = df[pm["current_mask"]], df[pm["previous_mask"]]
    if cur.empty or prev.empty:
        return {"status": "skipped", "reason": "One of the two periods contains no data."}
    r0, r1 = float(prev["revenue"].sum()), float(cur["revenue"].sum())
    q0 = float((prev["quantity"] if "quantity" in prev else pd.Series(1.0, index=prev.index)).sum())
    if r0 <= 0 or q0 <= 0:
        return {"status": "skipped", "reason": "The earlier period has no revenue to compare against."}

    dims = _segment_dims(df)
    t = decompose(cur, prev, dims)
    total = r1 - r0
    reconcile = float(t[["volume", "mix", "price"]].sum().sum() - total)
    t["pts"] = 100 * t["delta"] / r0
    segs = t.reindex(t["delta"].abs().sort_values(ascending=False).index).head(5)
    top_segments = [
        {
            "segment": _label(i),
            "delta": round(float(r.delta), 2),
            "pts": round(float(r.pts), 2),
            "price_effect": round(float(r.price), 2),
            "volume_effect": round(float(r.volume), 2),
            "mix_effect": round(float(r.mix), 2),
            "revenue_previous": round(float(r.R0), 2),
            "revenue_current": round(float(r.R1), 2),
        }
        for i, r in segs.iterrows()
    ]

    by_dim = {}
    for k, dim in enumerate(dims):
        g = t.groupby(level=k)["delta"].sum() if isinstance(t.index, pd.MultiIndex) else t["delta"]
        g = g.reindex(g.abs().sort_values(ascending=False).index).head(3)
        by_dim[dim] = [{"value": str(v), "delta": round(float(d), 2), "pts": round(100 * float(d) / r0, 2)} for v, d in g.items()]

    movers = []
    if "product" in df and "product" not in dims:
        pr = pd.DataFrame({"prev": prev.groupby("product")["revenue"].sum(), "cur": cur.groupby("product")["revenue"].sum()}).fillna(0.0)
        pr["delta"] = pr["cur"] - pr["prev"]
        movers = [
            {"product": str(i), "delta": round(float(r.delta), 2)}
            for i, r in pr.reindex(pr["delta"].abs().sort_values(ascending=False).index).head(5).iterrows()
        ]

    ml = _ml_explain(df, pm)
    return {
        "status": "ok",
        "basis": pm["basis"],
        "current_label": pm["current_label"],
        "previous_label": pm["previous_label"],
        "revenue_previous": round(r0, 2),
        "revenue_current": round(r1, 2),
        "change_abs": round(total, 2),
        "change_pct": round(100 * total / r0, 2),
        "segment_dimensions": dims or ["(none)"],
        "effects": {k: round(float(t[k].sum()), 2) for k in ("price", "volume", "mix")},
        "reconciles": bool(abs(reconcile) < 1e-6 * max(1.0, abs(total), r0)),
        "reconcile_error": round(reconcile, 9),
        "top_segments": top_segments,
        "by_dimension": by_dim,
        "product_movers": movers,
        "ml_explanation": ml,
    }


def main_driver(res: dict) -> tuple[dict, dict | None]:
    """(biggest contributor in the direction of the total change, largest opposing segment or None)."""
    segs = res["top_segments"]
    sign = 1 if res["change_abs"] >= 0 else -1
    same = [x for x in segs if x["delta"] * sign > 0]
    driver = same[0] if same else segs[0]
    opposing = next((x for x in segs if x["delta"] * sign < 0), None)
    return driver, opposing


def signed_money(v: float) -> str:
    """+$1,112 / -$74,000 (sign before the currency symbol)."""
    return f"{'+' if v >= 0 else '-'}${abs(v):,.0f}"


def drivers_insights(res: dict) -> list[dict]:
    if res["status"] != "ok":
        return [
            {
                "id": "ml-drivers-skipped",
                "type": "info",
                "severity": "Info",
                "title": "Revenue Drivers: not available",
                "desc": res["reason"],
                "recommendation": "Upload data covering at least two periods.",
            }
        ]
    ch = res["change_pct"]
    top, offset = main_driver(res)
    word = "rose" if ch >= 0 else "fell"
    pct_txt = f"{abs(ch):.1f}%" if abs(ch) < 10 else f"{abs(ch):.0f}%"
    eff = res["effects"]
    desc = (
        f"Revenue went from ${res['revenue_previous']:,.0f} to ${res['revenue_current']:,.0f} "
        f"({res['previous_label']} to {res['current_label']}). Price effect {signed_money(eff['price'])}, volume effect "
        f"{signed_money(eff['volume'])}, mix effect {signed_money(eff['mix'])}; these sum exactly to the change."
    )
    if offset:
        desc += f" Partly offset by {offset['segment']} ({offset['pts']:+.1f} pts)."
    ml = res["ml_explanation"]
    if ml["status"] == "ok" and ml["model_quality"] == "good" and ml["factors"]:
        f = ml["factors"][0]
        desc += f" The ML explanation (R^2 {ml['holdout_r2']:.2f}) ranks '{f['label']}' as the biggest factor ({f['direction']})."
    neg = ch < 0
    return [
        {
            "id": "ml-drivers-1",
            "type": "info",
            "severity": "Medium" if abs(ch) >= 10 else "Info",
            "title": f"Revenue Drivers: {res['current_label']} revenue {word} {pct_txt}, driven mainly by {top['segment']} ({top['pts']:+.1f} pts)",
            "desc": desc,
            "recommendation": (
                f"Investigate {top['segment']}: check pricing, stock and demand changes there."
                if neg
                else f"Find out what worked in {top['segment']} and repeat it elsewhere."
            ),
        }
    ]
