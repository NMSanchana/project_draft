"""ML Module 1: customer segmentation (RFM + K-Means) and churn-risk prediction.

Plain idea: sort customers into types (like a shopkeeper who knows regulars from drifters), then warn
who is about to leave.

Segmentation
  Recency / Frequency / Monetary per customer -> log1p -> StandardScaler -> K-Means with k chosen by
  silhouette over k in [3, 6] (random_state fixed). Clusters are named from centroid ranks.

Churn (no leakage)
  * ``W`` (the churn window) = 1.5 x the median gap between a customer's purchases (clamped), or a
    fraction of the data span when too few customers repurchase.
  * The data is split at ``cutoff = last_date - W``. **Features use only rows <= cutoff**; the label
    ("no purchase in the W days after the cutoff") uses rows > cutoff. Only customers still *active*
    at the cutoff (last purchase within 2W) are modelled, so the task is not trivially easy.
  * Logistic regression and gradient boosting are compared on a stratified hold-out by ROC-AUC.
  * The chosen model then scores customers as of today (same feature definitions, looking back from
    the last date). With < 200 modelled customers or a single class, a transparent heuristic is used
    and the output says so.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
MIN_CUSTOMERS = 20
MIN_MODEL_CUSTOMERS = 200
FEATURES = ["recency", "frequency", "monetary", "avg_gap", "overdue_ratio", "tenure", "recent_freq", "recent_share", "aov"]


# ----------------------------------------------------------------------------- helpers
def _purchases(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (customer, order/day) with revenue, excluding the imputed 'Unknown' customer."""
    d = df[df["customer"] != "Unknown"]
    key = d["order_id"] if "order_id" in d else d["date"].dt.normalize()
    return d.assign(_k=key).groupby(["customer", "_k"], as_index=False).agg(date=("date", "min"), revenue=("revenue", "sum"))


def rfm_table(df: pd.DataFrame) -> pd.DataFrame:
    p = _purchases(df)
    snap = df["date"].max().normalize() + pd.Timedelta(days=1)
    g = p.groupby("customer")
    return pd.DataFrame(
        {
            "recency": (snap - g["date"].max().dt.normalize()).dt.days.astype(float),
            "frequency": g.size().astype(float),
            "monetary": g["revenue"].sum(),
        }
    )


def _name_clusters(cent: pd.DataFrame) -> dict[int, str]:
    """Name clusters from centroid ranks (cent has mean recency/frequency/monetary per cluster id)."""
    r = lambda s: s.rank(pct=True) if len(s) > 1 else s * 0 + 0.5  # noqa: E731
    rec_good, f, m = 1 - r(cent["recency"]), r(cent["frequency"]), r(cent["monetary"])
    composite = rec_good + f + m
    names: dict[int, str] = {}
    left = set(cent.index)

    def take(name: str, key: pd.Series, ok=None) -> None:
        cand = [c for c in left if ok is None or ok(c)]
        if cand and name not in names.values():
            pick = max(cand, key=lambda c: (key[c], -c))
            names[pick] = name
            left.discard(pick)

    take("Champions", composite)
    take("Hibernating", -composite)
    take("At Risk", f + m, ok=lambda c: cent.loc[c, "recency"] > cent["recency"].median())
    take("Big Spenders", m)
    take("Loyal", f)
    take("Promising", rec_good)
    for c in sorted(left):
        names[c] = "Occasional"
    return names


# ----------------------------------------------------------------------------- segmentation
def run_segments(df: pd.DataFrame) -> dict:
    if "customer" not in df:
        return {"status": "skipped", "reason": "No customer column found. Add a customer id column to segment customers."}
    rfm = rfm_table(df)
    if len(rfm) < MIN_CUSTOMERS:
        return {"status": "skipped", "reason": f"Need at least {MIN_CUSTOMERS} distinct customers to segment (found {len(rfm)})."}

    X = StandardScaler().fit_transform(np.log1p(rfm[["recency", "frequency", "monetary"]].values))
    scores, models = {}, {}
    for k in range(3, 7):
        if k >= len(rfm):
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(X)
        if len(set(km.labels_)) < k:
            continue
        scores[k], models[k] = float(silhouette_score(X, km.labels_)), km
    if not scores:
        return {"status": "skipped", "reason": "Customers are too similar to form distinct segments."}
    best_k = max(scores, key=lambda k: (round(scores[k], 6), -k))
    rfm["cluster"] = models[best_k].labels_
    cent = rfm.groupby("cluster")[["recency", "frequency", "monetary"]].mean()
    names = _name_clusters(cent)
    rfm["segment"] = rfm["cluster"].map(names)

    total_rev = float(rfm["monetary"].sum())
    segs = []
    for name, g in rfm.groupby("segment"):
        top = g.sort_values("monetary", ascending=False).head(5)
        segs.append(
            {
                "name": name,
                "customers": int(len(g)),
                "customers_share_pct": round(100 * len(g) / len(rfm), 1),
                "revenue": round(float(g["monetary"].sum()), 2),
                "revenue_share_pct": round(100 * float(g["monetary"].sum()) / total_rev, 1),
                "avg_recency_days": round(float(g["recency"].mean()), 1),
                "avg_frequency": round(float(g["frequency"].mean()), 2),
                "avg_monetary": round(float(g["monetary"].mean()), 2),
                "top_customers": [
                    {
                        "customer": str(i),
                        "monetary": round(float(r.monetary), 2),
                        "recency_days": int(r.recency),
                        "frequency": int(r.frequency),
                    }
                    for i, r in top.iterrows()
                ],
            }
        )
    segs.sort(key=lambda s: -s["revenue"])
    return {
        "status": "ok",
        "method": "RFM + K-Means (k by silhouette)",
        "k": best_k,
        "silhouette": {str(k): round(v, 3) for k, v in scores.items()},
        "customers": int(len(rfm)),
        "segments": segs,
    }


# ----------------------------------------------------------------------------- churn
def churn_window(p: pd.DataFrame, span_days: float) -> tuple[int, str]:
    """Churn window W in days and a note on how it was derived."""
    gaps = p.sort_values("date").groupby("customer")["date"].diff().dt.days.dropna()
    gaps = gaps[gaps > 0]
    repeaters = p.groupby("customer").size().ge(2).sum()
    if repeaters >= 30 and len(gaps):
        w = int(np.clip(round(1.5 * float(gaps.median())), 14, max(14, span_days / 3)))
        return w, f"1.5 x the median gap between purchases ({gaps.median():.0f} days)"
    w = int(np.clip(round(span_days / 6), 14, 90))
    return w, "one sixth of the data span (too few repeat customers to measure purchase gaps)"


def build_features(p: pd.DataFrame, asof: pd.Timestamp, window: int) -> pd.DataFrame:
    """Customer features using ONLY purchases dated <= ``asof`` (the no-leakage guarantee)."""
    h = p[p["date"] <= asof]
    g = h.groupby("customer")
    last, first = g["date"].max(), g["date"].min()
    freq, mon = g.size().astype(float), g["revenue"].sum()
    recent = h[h["date"] > asof - pd.Timedelta(days=window)].groupby("customer")
    gap_med = h.sort_values("date").groupby("customer")["date"].diff().dt.days.dropna()
    gap_med = float(gap_med[gap_med > 0].median()) if (gap_med > 0).any() else float(window)
    mean_gap = h.sort_values("date").groupby("customer")["date"].diff().dt.days.groupby(h.sort_values("date")["customer"]).mean()
    out = pd.DataFrame(
        {
            "recency": (asof - last).dt.days.astype(float),
            "frequency": freq,
            "monetary": mon,
            "avg_gap": mean_gap.reindex(freq.index).fillna(gap_med),
            "tenure": (asof - first).dt.days.astype(float),
            "recent_freq": recent.size().reindex(freq.index).fillna(0.0),
            "recent_share": (recent["revenue"].sum().reindex(freq.index).fillna(0.0) / mon.replace(0, np.nan)).fillna(0.0),
            "aov": mon / freq,
        }
    )
    out["overdue_ratio"] = out["recency"] / out["avg_gap"].clip(lower=1.0)  # how overdue vs the customer's own rhythm
    return out[FEATURES]


def run_churn(df: pd.DataFrame, window_days: int | None = None) -> dict:
    if "customer" not in df:
        return {"status": "skipped", "reason": "No customer column found."}
    p = _purchases(df)
    n_customers = p["customer"].nunique()
    if n_customers < MIN_CUSTOMERS:
        return {"status": "skipped", "reason": f"Need at least {MIN_CUSTOMERS} distinct customers (found {n_customers})."}
    last_date = p["date"].max().normalize()
    span = (last_date - p["date"].min().normalize()).days
    if span < 28:
        return {"status": "skipped", "reason": f"Need at least 28 days of history to define churn (found {span})."}

    w, w_note = (window_days, "set by caller") if window_days else churn_window(p, span)
    cutoff = last_date - pd.Timedelta(days=w)
    total_rev = float(p["revenue"].sum())

    # ---- training set: features <= cutoff, label from (cutoff, last_date] ----
    train_feat = build_features(p, cutoff, w)
    train_feat = train_feat[train_feat["recency"] <= 2 * w]  # still active at the cutoff
    future = set(p.loc[p["date"] > cutoff, "customer"])
    y = pd.Series([0 if c in future else 1 for c in train_feat.index], index=train_feat.index)
    now_feat = build_features(p, last_date, w)
    active_now = now_feat[now_feat["recency"] <= 2 * w]

    base = {
        "window_days": w,
        "window_rule": w_note,
        "cutoff_date": cutoff.strftime("%Y-%m-%d"),
        "customers_total": int(n_customers),
        "modelled_customers": int(len(train_feat)),
        "churn_rate_in_training": round(float(y.mean()), 3) if len(y) else None,
        "lapsed_customers": int((now_feat["recency"] > 2 * w).sum()),
        "leakage_guard": "features use only purchases dated on/before the cutoff; labels use the window after it",
    }

    use_model = len(train_feat) >= MIN_MODEL_CUSTOMERS and y.nunique() == 2 and y.value_counts().min() >= 10
    if use_model:
        Xtr, Xte, ytr, yte = train_test_split(train_feat, y, test_size=0.3, stratify=y, random_state=SEED)
        cands = {
            "Logistic Regression": make_pipeline(
                StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED)
            ),
            "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=2, random_state=SEED),
        }
        board = []
        for name, m in cands.items():
            m.fit(Xtr, ytr)
            proba = m.predict_proba(Xte)[:, 1]
            pred = (proba >= 0.5).astype(int)
            board.append(
                {
                    "model": name,
                    "roc_auc": round(float(roc_auc_score(yte, proba)), 3),
                    "precision": round(float(precision_score(yte, pred, zero_division=0)), 3),
                    "recall": round(float(recall_score(yte, pred, zero_division=0)), 3),
                }
            )
        board.sort(key=lambda b: -b["roc_auc"])
        best = board[0]
        final = cands[best["model"]].fit(train_feat, y)
        prob = pd.Series(final.predict_proba(active_now)[:, 1], index=active_now.index)
        method, status = "model", ("ok" if best["roc_auc"] >= 0.6 else "unreliable")
        extra = {"model": best["model"], "metrics": best, "leaderboard": board, "holdout_customers": int(len(yte))}
        if status == "unreliable":
            extra["reason"] = f"Best model ROC-AUC is only {best['roc_auc']:.2f}; treat churn scores as indicative."
    else:
        prob = (active_now["recency"] / (2 * w)).clip(0, 1)
        method, status = "heuristic", "ok"
        extra = {
            "reason": (
                "Too little data for a trained model (need >= 200 active customers and both outcomes); "
                "using a transparent heuristic: risk = days since last purchase / (2 x churn window)."
            )
        }

    at_risk = prob[prob >= 0.5].sort_values(ascending=False)
    top = [
        {
            "customer": str(c),
            "churn_probability": round(float(prob[c]), 3),
            "recency_days": int(now_feat.loc[c, "recency"]),
            "frequency": int(now_feat.loc[c, "frequency"]),
            "monetary": round(float(now_feat.loc[c, "monetary"]), 2),
        }
        for c in prob.sort_values(ascending=False).head(10).index
    ]
    risk_rev = float(now_feat.loc[at_risk.index, "monetary"].sum())
    return {
        "status": status,
        "method": method,
        **base,
        **extra,
        "active_customers": int(len(active_now)),
        "at_risk_customers": int(len(at_risk)),
        "at_risk_revenue": round(risk_rev, 2),
        "at_risk_revenue_share_pct": round(100 * risk_rev / total_rev, 1) if total_rev else 0.0,
        "top_at_risk": top,
    }


# ----------------------------------------------------------------------------- insights
def rfm_insights(seg: dict, churn: dict) -> list[dict]:
    out: list[dict] = []
    if seg["status"] != "ok":
        out.append(
            {
                "id": "ml-rfm-skipped",
                "type": "info",
                "severity": "Info",
                "title": "Customer Segments: not enough data",
                "desc": seg["reason"],
                "recommendation": "Provide a customer id, date and revenue column with at least 20 customers.",
            }
        )
        return out
    by = {s["name"]: s for s in seg["segments"]}
    risky = by.get("At Risk") or by.get("Hibernating")
    if risky:
        out.append(
            {
                "id": "ml-rfm-1",
                "type": "alert",
                "severity": "High" if risky["revenue_share_pct"] >= 20 else "Medium",
                "title": f"Customer Segments: {risky['customers']} customers {risky['name'].lower()}, {risky['revenue_share_pct']:.0f}% of revenue",
                "desc": (
                    f"The '{risky['name']}' segment has {risky['customers']} customers who bought on average "
                    f"{risky['avg_recency_days']:.0f} days ago, {risky['avg_frequency']:.1f} times, ${risky['avg_monetary']:,.0f} each."
                ),
                "recommendation": "Run a win-back campaign (personal offer or reminder) for this group.",
            }
        )
    champ = by.get("Champions")
    if champ:
        out.append(
            {
                "id": "ml-rfm-2",
                "type": "growth",
                "severity": "Info",
                "title": f"Customer Segments: {champ['customers']} Champions drive {champ['revenue_share_pct']:.0f}% of revenue",
                "desc": f"Champions buy often ({champ['avg_frequency']:.1f} orders), recently ({champ['avg_recency_days']:.0f} days ago) and spend ${champ['avg_monetary']:,.0f} each.",
                "recommendation": "Reward them with early access or loyalty perks to keep them.",
            }
        )
    if churn["status"] in ("ok", "unreliable") and churn["at_risk_customers"]:
        how = (
            f"model: {churn['model']}, ROC-AUC {churn['metrics']['roc_auc']:.2f}"
            if churn["method"] == "model"
            else "heuristic score, too little data for a model"
        )
        out.append(
            {
                "id": "ml-churn-1",
                "type": "alert",
                "severity": "Medium",
                "title": f"Churn Risk: {churn['at_risk_customers']} active customers likely to lapse",
                "desc": (
                    f"{churn['at_risk_customers']} of {churn['active_customers']} active customers have a churn probability of 50% or more, "
                    f"representing {churn['at_risk_revenue_share_pct']:.0f}% of historical revenue ({how}). "
                    f"Churn means no purchase within {churn['window_days']} days."
                ),
                "recommendation": "Contact the top at-risk customers first; the list is in the churn module output.",
            }
        )
    return out
