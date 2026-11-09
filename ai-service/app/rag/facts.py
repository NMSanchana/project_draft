"""Dataset-fact RAG: index the dataset's own computed facts as short documents in ``data_<datasetId>``.

This lets the chat retrieve *explanations* (why, which segment, what the model found), not only numbers.
"""

from __future__ import annotations

import pandas as pd

from . import store
from .chunking import Chunk
from .embeddings import get_embedder


def _money(v: float) -> str:
    return f"${v:,.0f}"


def build_fact_docs(df: pd.DataFrame, analytics: dict, modules: dict) -> list[tuple[str, str]]:
    """Return ``[(title, text)]``: one short fact document per topic."""
    q = analytics.get("quality") or {}
    kp = analytics.get("kpis") or {}
    docs: list[tuple[str, str]] = []
    roles = ", ".join(f"{r} = column '{v['column']}'" for r, v in (q.get("detected_roles") or {}).items())
    docs.append(
        (
            "Dataset schema",
            f"File {analytics['fileName']} has {analytics['recordsCount']} cleaned rows covering "
            f"{q.get('date_range', ['?', '?'])[0]} to {q.get('date_range', ['?', '?'])[1]}. Detected columns: {roles}. "
            f"Data quality score {q.get('quality_score', 'n/a')} out of 100.",
        )
    )
    docs.append(
        (
            "Key metrics",
            f"Revenue {_money(analytics['revenue'])}, cost {_money(analytics['totalCost'])}, profit "
            f"{_money(analytics['totalProfit'])}, profit margin {analytics['profitMargin']}%, {analytics['orders']} orders, "
            f"{analytics['uniqueCustomers']} unique customers, average order value ${kp.get('avg_order_value', 0):,.2f}.",
        )
    )
    for col in ("category", "region", "product"):
        if col in df:
            g = df.groupby(col)["revenue"].sum().sort_values(ascending=False)
            tot = float(g.sum()) or 1.0
            parts = "; ".join(f"{k}: {_money(v)} ({100 * v / tot:.1f}%)" for k, v in g.head(8).items())
            docs.append((f"Revenue by {col}", f"Revenue by {col} (largest first): {parts}."))
    pc = kp.get("period_change")
    if pc and pc.get("change_pct") is not None:
        docs.append(
            (
                "Period change",
                f"Revenue went from {_money(pc['previous_revenue'])} in {pc['previous_label']} to "
                f"{_money(pc['current_revenue'])} in {pc['current_label']}, a change of {pc['change_pct']}%.",
            )
        )
    for ins in analytics.get("insights", []):
        docs.append((f"Insight: {ins['title'][:60]}", f"{ins['title']}. {ins['desc']} Recommendation: {ins['recommendation']}"))
    dr = modules.get("drivers") or {}
    if dr.get("status") == "ok":
        segs = "; ".join(f"{s['segment']} {s['delta']:+,.0f} ({s['pts']:+.1f} pts)" for s in dr["top_segments"])
        e = dr["effects"]
        docs.append(
            (
                "Revenue drivers detail",
                f"Why revenue changed {dr['previous_label']} to {dr['current_label']} ({dr['change_pct']}%): "
                f"price effect {e['price']:+,.0f}, volume effect {e['volume']:+,.0f}, mix effect {e['mix']:+,.0f}. Biggest segment movers: {segs}.",
            )
        )
    pr = modules.get("pricing") or {}
    if pr.get("segments"):
        lines = "; ".join(
            f"{s['segment']}: elasticity {s['elasticity']}" if s["reliability"] == "reliable" else f"{s['segment']}: insufficient evidence"
            for s in pr["segments"][:8]
        )
        docs.append(("Price elasticity detail", f"Price elasticity by segment: {lines}."))
    bk = modules.get("basket") or {}
    if bk.get("rules"):
        docs.append(
            (
                "Cross-sell rules",
                "Products bought together: "
                + "; ".join(
                    f"{r['antecedent']} -> {r['consequent']} (lift {r['lift']}, confidence {100 * r['confidence']:.0f}%)"
                    for r in bk["rules"][:5]
                )
                + ".",
            )
        )
    ch = modules.get("churn") or {}
    if ch.get("top_at_risk"):
        docs.append(
            (
                "Churn risk detail",
                f"Churn means no purchase within {ch['window_days']} days. Top at-risk customers: "
                + "; ".join(f"{t['customer']} ({100 * t['churn_probability']:.0f}%)" for t in ch["top_at_risk"][:5])
                + ".",
            )
        )
    return [(t, x) for t, x in docs if x.strip()]


def index_dataset(dataset_id: str, df: pd.DataFrame, analytics: dict, modules: dict) -> int:
    """Recreate ``data_<datasetId>`` from the current facts. Returns the number of fact chunks."""
    docs = build_fact_docs(df, analytics, modules)
    col = store.data_collection(dataset_id)
    store.delete_collection(col)
    store.ensure_collection(col)
    chunks = [Chunk(text=f"{t}: {x}", page=1, chunk_id=i) for i, (t, x) in enumerate(docs)]
    vectors = get_embedder().encode([c.text for c in chunks])
    # one upsert per fact so each keeps its own citation label
    for (t, _), ch, vec in zip(docs, chunks, vectors):
        store.upsert_chunks(col, f"facts-{dataset_id}", f"dataset facts: {t}", [ch], [vec], {"scope": "facts"})
    return len(chunks)
