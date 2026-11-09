"""ML Module 4: cross-sell rules (market-basket analysis).

Plain idea: "people who buy X also buy Y", like a shop assistant who pairs things for you.

Baskets are grouped by ``order_id`` when orders contain several lines, otherwise by customer + date.
Items are products (or categories when there is no product column). FP-Growth finds frequent item
sets; rules ``A -> B`` are scored by

  support    = share of baskets containing both
  confidence = P(B | A)
  lift       = confidence / P(B)    (lift > 1 means A and B appear together more than chance)

Only rules with lift > 1.2 and at least 5 co-occurring baskets are kept (top 10).
"""

from __future__ import annotations

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth

MIN_LIFT = 1.2
MIN_COOCCUR = 5
MIN_MULTI_BASKETS = 30
MAX_ITEMS = 200
TOP_N = 10


def _baskets(df: pd.DataFrame) -> tuple[pd.Series, str, str] | None:
    item = "product" if "product" in df else ("category" if "category" in df else None)
    if item is None:
        return None
    candidates = []
    if "order_id" in df:
        candidates.append(("order_id", df["order_id"].astype(str)))
    if "customer" in df:
        candidates.append(("customer + date", df["customer"].astype(str) + "|" + df["date"].dt.strftime("%Y-%m-%d")))
    best = None
    for basis, key in candidates:
        multi = int((df.groupby(key)[item].nunique() >= 2).sum())
        if best is None or multi > best[0]:
            best = (multi, basis, key)
    if best is None:
        return None
    return best[2], best[1], item


def run_basket(df: pd.DataFrame) -> dict:
    found = _baskets(df)
    if found is None:
        return {
            "status": "skipped",
            "reason": "Cross-sell analysis needs a product (or category) column plus an order id or customer column.",
        }
    key, basis, item = found
    tx = df.groupby(key)[item].agg(lambda s: sorted(set(s.astype(str)))).rename("items")
    n_all = int(len(tx))
    tx = tx[tx.map(len) >= 2]
    if len(tx) < MIN_MULTI_BASKETS:
        return {
            "status": "skipped",
            "baskets": n_all,
            "basket_basis": basis,
            "item_level": item,
            "reason": (
                f"Only {len(tx)} of {n_all} baskets contain 2+ different {item}s (need {MIN_MULTI_BASKETS}); "
                "customers buy one item per order, so cross-sell rules cannot be mined."
            ),
        }

    top_items = df[item].astype(str).value_counts().head(MAX_ITEMS).index
    onehot = pd.DataFrame(False, index=range(len(tx)), columns=sorted(top_items))
    for i, items in enumerate(tx):
        for it in items:
            if it in onehot.columns:
                onehot.at[i, it] = True
    n = len(onehot)
    min_support = max(MIN_COOCCUR / n, 0.005)
    freq = fpgrowth(onehot, min_support=min_support, use_colnames=True)
    if freq.empty or (freq["itemsets"].map(len) >= 2).sum() == 0:
        return {
            "status": "ok",
            "basket_basis": basis,
            "item_level": item,
            "baskets": n_all,
            "multi_item_baskets": n,
            "min_support": round(min_support, 4),
            "rules": [],
            "reason": "No item pairs are bought together often enough to form reliable rules.",
        }
    rules = association_rules(freq, num_itemsets=n, metric="lift", min_threshold=MIN_LIFT)
    rules = rules[(rules["antecedents"].map(len) == 1) & (rules["consequents"].map(len) == 1)].copy()
    rules["co"] = (rules["support"] * n).round().astype(int)
    rules = rules[rules["co"] >= MIN_COOCCUR].sort_values(["lift", "confidence", "support"], ascending=False).head(TOP_N)
    out = [
        {
            "antecedent": next(iter(r.antecedents)),
            "consequent": next(iter(r.consequents)),
            "support": round(float(r.support), 4),
            "confidence": round(float(r.confidence), 4),
            "lift": round(float(r.lift), 3),
            "co_occurrences": int(r.co),
        }
        for r in rules.itertuples()
    ]
    return {
        "status": "ok",
        "method": "FP-Growth + association rules",
        "basket_basis": basis,
        "item_level": item,
        "baskets": n_all,
        "multi_item_baskets": n,
        "min_support": round(min_support, 4),
        "rules": out,
        **({} if out else {"reason": "No rules passed the lift and co-occurrence thresholds."}),
    }


def basket_insights(res: dict, limit: int = 3) -> list[dict]:
    if res["status"] == "skipped" or not res.get("rules"):
        return [
            {
                "id": "ml-basket-skipped",
                "type": "info",
                "severity": "Info",
                "title": "Cross-sell: no rules found",
                "desc": res.get("reason", "No reliable cross-sell rules."),
                "recommendation": "Cross-sell rules need orders with several different products.",
            }
        ]
    out = []
    for i, r in enumerate(res["rules"][:limit], 1):
        out.append(
            {
                "id": f"ml-basket-{i}",
                "type": "opportunity",
                "severity": "Medium" if r["lift"] >= 2 else "Low",
                "title": f"Cross-sell: {r['antecedent']} → {r['consequent']} (lift {r['lift']:.1f}, confidence {100 * r['confidence']:.0f}%)",
                "desc": (
                    f"Customers who buy {r['antecedent']} also buy {r['consequent']} {100 * r['confidence']:.0f}% of the time, "
                    f"{r['lift']:.1f}x more than chance ({r['co_occurrences']} orders)."
                ),
                "recommendation": f"Bundle {r['antecedent']} with {r['consequent']} or suggest {r['consequent']} at checkout.",
            }
        )
    return out
