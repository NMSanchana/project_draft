"""Rule-based insights: the teammate's README "Rule-Based Insights Catalog", with its exact thresholds.

| Rule id               | Trigger                         | Severity | Frontend type |
|-----------------------|---------------------------------|----------|---------------|
| strong-growth         | revenue growth  > +10%          | Low      | growth        |
| revenue-decline       | revenue growth  < -10%          | High     | alert         |
| declining-product     | product growth  < -15%          | Medium   | alert         |
| regional-opportunity  | region growth   > +20%          | Medium   | opportunity   |
| low-margin            | profit margin   < 15%           | High     | alert         |
| high-value-customer   | spend in top 10% of customers   | Info     | opportunity   |

Growth compares the last two full months (or the two halves of the data), see ``kpis.period_comparison``.
Per-entity rules ignore entities below 1% of the earlier period's revenue (too small to be meaningful).
"""

from __future__ import annotations

import math

import pandas as pd

GROWTH_UP, GROWTH_DOWN = 10.0, -10.0
PRODUCT_DECLINE, REGION_GROWTH, LOW_MARGIN = -15.0, 20.0, 15.0
MIN_SHARE = 0.01
MAX_PER_RULE = 3


def _m(v: float) -> str:
    return f"${v:,.0f}"


def _entity_growth(df: pd.DataFrame, cmp: dict, col: str) -> pd.DataFrame:
    cur = df.loc[cmp["current_mask"]].groupby(col)["revenue"].sum()
    prev = df.loc[cmp["previous_mask"]].groupby(col)["revenue"].sum()
    g = pd.DataFrame({"cur": cur, "prev": prev}).fillna(0.0)
    total_prev = float(prev.sum())
    g = g[(g["prev"] > 0) & (g["prev"] >= MIN_SHARE * total_prev)]
    g["growth"] = 100 * (g["cur"] - g["prev"]) / g["prev"]
    return g


def run_rules(df: pd.DataFrame, kpis: dict, cmp: dict | None) -> list[dict]:
    """Evaluate the catalog and return ``RuleInsight`` dicts."""
    out: list[dict] = []
    if cmp and cmp.get("change_pct") is not None:
        ch, span = cmp["change_pct"], f"{cmp['current_label']} vs {cmp['previous_label']}"
        if ch > GROWTH_UP:
            out.append(
                {
                    "id": "strong-growth",
                    "type": "growth",
                    "severity": "Low",
                    "title": f"Strong Growth Trend: revenue up {ch:.1f}%",
                    "desc": f"Revenue rose {ch:.1f}% ({span}): {_m(cmp['previous_revenue'])} to {_m(cmp['current_revenue'])}.",
                    "recommendation": "Expand inventory and double down on active marketing channels.",
                }
            )
        elif ch < GROWTH_DOWN:
            out.append(
                {
                    "id": "revenue-decline",
                    "type": "alert",
                    "severity": "High",
                    "title": f"Revenue Decline: revenue down {abs(ch):.1f}%",
                    "desc": f"Revenue fell {abs(ch):.1f}% ({span}): {_m(cmp['previous_revenue'])} to {_m(cmp['current_revenue'])}.",
                    "recommendation": "Review pricing models, customer feedback, and churn factors immediately.",
                }
            )

        item_col = "product" if "product" in df else ("category" if "category" in df else None)
        if item_col:
            g = _entity_growth(df, cmp, item_col)
            for i, (name, r) in enumerate(g[g["growth"] < PRODUCT_DECLINE].sort_values("growth").head(MAX_PER_RULE).iterrows(), 1):
                out.append(
                    {
                        "id": f"declining-product-{i}",
                        "type": "alert",
                        "severity": "Medium",
                        "title": f"Declining {item_col.title()}: {name} down {abs(r['growth']):.1f}%",
                        "desc": f"{name} revenue dropped from {_m(r['prev'])} to {_m(r['cur'])} ({span}).",
                        "recommendation": "Re-evaluate product positioning or initiate targeted promotional offers.",
                    }
                )
        if "region" in df:
            g = _entity_growth(df, cmp, "region")
            for i, (name, r) in enumerate(
                g[g["growth"] > REGION_GROWTH].sort_values("growth", ascending=False).head(MAX_PER_RULE).iterrows(), 1
            ):
                out.append(
                    {
                        "id": f"regional-opportunity-{i}",
                        "type": "opportunity",
                        "severity": "Medium",
                        "title": f"High Growth Region: {name} up {r['growth']:.1f}%",
                        "desc": f"{name} revenue grew from {_m(r['prev'])} to {_m(r['cur'])} ({span}).",
                        "recommendation": "Increase sales resource allocation and supply chain support in this region.",
                    }
                )

    if kpis["has_cost"]:
        if kpis["profit_margin_pct"] < LOW_MARGIN:
            out.append(
                {
                    "id": "low-margin",
                    "type": "alert",
                    "severity": "High",
                    "title": f"Low Profit Margin: {kpis['profit_margin_pct']:.1f}%",
                    "desc": f"Overall margin is {kpis['profit_margin_pct']:.1f}% on {_m(kpis['revenue'])} revenue, below the {LOW_MARGIN:.0f}% threshold.",
                    "recommendation": "Audit product cost structure or consider supplier renegotiation.",
                }
            )
        item_col = "product" if "product" in df else ("category" if "category" in df else None)
        if item_col:
            g = df.groupby(item_col).agg(rev=("revenue", "sum"), cost=("cost", "sum"))
            g = g[g["rev"] >= MIN_SHARE * g["rev"].sum()]
            g["margin"] = 100 * (g["rev"] - g["cost"]) / g["rev"]
            for i, (name, r) in enumerate(g[g["margin"] < LOW_MARGIN].sort_values("margin").head(MAX_PER_RULE).iterrows(), 1):
                out.append(
                    {
                        "id": f"low-margin-{item_col}-{i}",
                        "type": "alert",
                        "severity": "High",
                        "title": f"Low Margin {item_col.title()}: {name} at {r['margin']:.1f}%",
                        "desc": f"{name} earns {r['margin']:.1f}% margin on {_m(r['rev'])} revenue (threshold {LOW_MARGIN:.0f}%).",
                        "recommendation": "Audit product cost structure or consider supplier renegotiation.",
                    }
                )

    if "customer" in df and df["customer"].nunique() >= 10:
        spend = df.groupby("customer")["revenue"].sum().sort_values(ascending=False)
        k = max(1, math.ceil(0.10 * len(spend)))
        share = 100 * float(spend.head(k).sum()) / float(spend.sum())
        top = ", ".join(str(c) for c in spend.head(3).index)
        out.append(
            {
                "id": "high-value-customer",
                "type": "opportunity",
                "severity": "Info",
                "title": f"High-Value Customers: top {k} customers drive {share:.0f}% of revenue",
                "desc": f"The top 10% of customers ({k} of {len(spend)}) generate {share:.1f}% of revenue. Largest: {top}.",
                "recommendation": "Introduce dedicated loyalty rewards or account management outreach.",
            }
        )
    return out
