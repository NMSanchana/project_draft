"""Anomaly detection on daily revenue with root-cause attribution.

A day is flagged only when **both** detectors agree:
  * robust z-score (median/MAD, "modified z") >= 4.0 on the weekday-adjusted value, and
  * IsolationForest (contamination 5%) marks it an outlier.
Weekday adjustment divides each day by its weekday's median share (when >= 4 weeks of data).
Each day is compared with its *local* level (centred 29-day rolling median), so growth or decline is not mistaken for
anomalies. Both detectors run on the log ratio to that level: revenue noise is multiplicative (a few big orders swing a
day), so on the log scale a day at 12% of normal is as extreme as one at 8x normal.

Root cause: for a flagged day, per dimension (category, region, product, customer) the contribution
is ``revenue_that_day - typical_daily_revenue`` (typical = mean over non-flagged days). The share of
the day's total deviation is reported; the dimension value with the largest share is the headline cause.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

Z_THRESHOLD = 4.0
MIN_DAYS = 14
DIMENSIONS = ["category", "region", "product", "customer"]


def _modified_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    if mad > 0:
        return 0.6745 * (x - med) / mad
    sd = x.std()
    return (x - med) / sd if sd > 0 else np.zeros_like(x)


def _weekday_factors(s: pd.Series) -> np.ndarray:
    """Per-day weekday factor (1.0 when there are < 4 weeks of data)."""
    vals = s.values.astype(float)
    if len(s) < 28:
        return np.ones(len(s))
    dow = s.index.dayofweek.values
    med = np.median(vals) or 1.0
    factor = np.ones(7)
    for d in range(7):
        m = vals[dow == d]
        if len(m):
            factor[d] = max(np.median(m) / med, 0.05)
    return factor[dow]


def _local_level(adj: np.ndarray) -> np.ndarray:
    """Typical level around each day: centred 29-day rolling median (robust to the anomaly itself)."""
    glob = float(np.median(adj)) or 1.0
    if len(adj) < 28:
        return np.full(len(adj), glob)
    lvl = pd.Series(adj).rolling(29, center=True, min_periods=7).median().to_numpy()
    return np.where(np.isfinite(lvl) & (lvl > 0), lvl, glob)


def _causes(df: pd.DataFrame, day: pd.Timestamp, normal_days: int, flagged: set, total_dev: float) -> list[dict]:
    d = df["date"].dt.normalize()
    on_day = df[d == day]
    normal = df[~d.isin(flagged)]
    out = []
    for dim in DIMENSIONS:
        if dim not in df:
            continue
        today = on_day.groupby(dim)["revenue"].sum()
        typical = normal.groupby(dim)["revenue"].sum() / max(normal_days, 1)
        contrib = today.reindex(today.index.union(typical.index)).fillna(0.0) - typical.reindex(today.index.union(typical.index)).fillna(
            0.0
        )
        if contrib.empty or total_dev == 0:
            continue
        pick = contrib.abs().idxmax()
        out.append(
            {
                "dimension": dim,
                "value": str(pick),
                "contribution": round(float(contrib[pick]), 2),
                "share_pct": round(100 * float(contrib[pick]) / total_dev, 1),
            }
        )
    out.sort(key=lambda c: -abs(c["share_pct"]))
    return out


def run_anomalies(df: pd.DataFrame) -> dict:
    """Return the anomalies module result."""
    s = df.groupby(df["date"].dt.normalize())["revenue"].sum()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"), fill_value=0.0)
    if len(s) < MIN_DAYS:
        return {"status": "skipped", "reason": f"Need at least {MIN_DAYS} days of data to detect anomalies (found {len(s)})."}

    factor = _weekday_factors(s)
    adj_raw = s.values.astype(float) / factor
    level = _local_level(adj_raw)
    expected = level * factor
    resid = np.log1p(np.clip(adj_raw, 0, None)) - np.log1p(level)  # log ratio to the local level
    z = _modified_z(resid)
    iso = IsolationForest(contamination=0.05, random_state=42).fit_predict(resid.reshape(-1, 1)) == -1
    flag = (np.abs(z) >= Z_THRESHOLD) & iso
    flagged_days = set(s.index[flag])
    normal_days = int((~flag).sum())

    items = []
    for i in np.where(flag)[0]:
        day, val, exp = s.index[i], float(s.iloc[i]), float(expected[i])
        total_dev = val - float(np.mean(s.values[~flag])) if normal_days else val - exp
        causes = _causes(df, day, normal_days, flagged_days, total_dev)
        direction = "spike" if val > exp else "dip"
        items.append(
            {
                "date": day.strftime("%Y-%m-%d"),
                "value": round(val, 2),
                "expected": round(exp, 2),
                "deviation_pct": round(100 * (val - exp) / exp, 1) if exp else None,
                "direction": direction,
                "robust_z": round(float(z[i]), 2),
                "causes": causes,
                "cause_text": (
                    f"{causes[0]['value']} ({causes[0]['dimension']}) accounts for "
                    f"{abs(causes[0]['share_pct']):.0f}% of the {direction}"
                )
                if causes
                else "No single driver stands out",
            }
        )
    items.sort(key=lambda a: -abs(a["robust_z"]))
    return {
        "status": "ok",
        "method": "robust z-score (|z|>=4.0) AND IsolationForest must agree",
        "days_analyzed": int(len(s)),
        "count": len(items),
        "anomalies": items,
    }


def anomaly_insights(res: dict, limit: int = 3) -> list[dict]:
    if res.get("status") != "ok" or not res["anomalies"]:
        return []
    out = []
    for i, a in enumerate(res["anomalies"][:limit], 1):
        dip = a["direction"] == "dip"
        pct = f"{a['deviation_pct']:+.0f}%" if a["deviation_pct"] is not None else ""
        out.append(
            {
                "id": f"ml-anomaly-{i}",
                "type": "alert" if dip else "info",
                "severity": "Medium" if dip else "Info",
                "title": f"Anomaly: revenue {a['direction']} on {a['date']} ({pct})",
                "desc": (f"Revenue was ${a['value']:,.0f} versus about ${a['expected']:,.0f} expected. {a['cause_text']}."),
                "recommendation": (
                    "Check stock-outs, outages or lost orders that day."
                    if dip
                    else "Check whether this was a promotion or one large order, and whether it can be repeated."
                ),
            }
        )
    return out
