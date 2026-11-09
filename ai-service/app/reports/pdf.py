"""Server-side PDF report (reportlab + matplotlib).

Sections: data quality, KPIs, trend, insights, forecast, anomalies, segments & churn, revenue drivers,
pricing, cross-sell, documents. A section whose module did not run says ``Not available: <reason>``
instead of disappearing. One failing section never prevents the rest of the report from being built.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from xml.sax.saxutils import escape

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

log = logging.getLogger(__name__)
GREEN, DARK, GREY = "#54bd95", "#0f172a", "#64748b"
_SS = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_SS["Heading1"], textColor=colors.HexColor(DARK), spaceBefore=6, spaceAfter=6, fontSize=16, keepWithNext=1)
H2 = ParagraphStyle("H2", parent=_SS["Heading2"], textColor=colors.HexColor(DARK), spaceBefore=8, spaceAfter=4, fontSize=12, keepWithNext=1)
BODY = ParagraphStyle("B", parent=_SS["BodyText"], fontSize=9.5, leading=13)
SMALL = ParagraphStyle("S", parent=BODY, fontSize=8, textColor=colors.HexColor(GREY))
NA = ParagraphStyle("NA", parent=BODY, textColor=colors.HexColor("#9a3412"), backColor=colors.HexColor("#fff7ed"), borderPadding=4)


def _p(text: str, style=BODY) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def _money(v: float | None) -> str:
    return "n/a" if v is None else f"${v:,.0f}"


def _table(rows: list[list], widths=None, header=True) -> Table:
    data = [[c if hasattr(c, "wrap") else _p(c) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2f5ee"))]
    t.setStyle(TableStyle(style))
    return t


def _chart(fig) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    img._restrictSize(17 * cm, 8 * cm)
    return img


def _na(module: str, res: dict | None) -> list:
    reason = (res or {}).get("reason") or "this module did not produce a result for this dataset"
    return [_p(f"Not available: {reason}", NA), Spacer(1, 6)]


def _usable(res: dict | None) -> bool:
    return bool(res) and res.get("status") in ("ok", "unreliable")


# ------------------------------------------------------------------------------ sections
def _sec_quality(a: dict, m: dict) -> list:
    q = a.get("quality") or {}
    out = [_p("1. Data quality", H1)]
    b = q.get("quality_breakdown", {})
    out.append(
        _p(
            f"Quality score {q.get('quality_score', 'n/a')} / 100 (completeness {b.get('completeness')}/40, uniqueness "
            f"{b.get('uniqueness')}/15, validity {b.get('validity')}/25, coverage {b.get('coverage')}/20). "
            f"Period {' to '.join(q.get('date_range', ['?', '?']))}."
        )
    )
    out.append(
        _p(
            f"Rows in {q.get('rows_in')}, rows analysed {q.get('rows_out')}: duplicates removed {q.get('duplicates_removed')}, "
            f"invalid dates {q.get('invalid_dates_removed')}, negative values {q.get('negative_rows_removed')}, "
            f"cancelled/returned orders excluded {q.get('status_excluded_rows', 0)}. Cost basis: {q.get('cost_basis') or 'no cost data'}."
        )
    )
    roles = q.get("detected_roles", {})
    if roles:
        out += [
            Spacer(1, 4),
            _table(
                [["Role", "Column", "Confidence"]]
                + [[r, v["column"], f"{v['confidence']:.2f}" if v.get("confidence") is not None else "-"] for r, v in roles.items()],
                [4 * cm, 7 * cm, 3 * cm],
            ),
        ]
    for n in q.get("notes", []):
        out.append(_p(f"Note: {n}", SMALL))
    return out


def _sec_kpis(a: dict, m: dict) -> list:
    k = a.get("kpis") or {}
    rows = [
        ["Metric", "Value"],
        ["Revenue", _money(a["revenue"])],
        ["Total cost", _money(a["totalCost"])],
        ["Profit", _money(a["totalProfit"])],
        ["Profit margin", f"{a['profitMargin']:.1f}%"],
        ["Orders", f"{a['orders']:,}"],
        ["Average order value", f"${k.get('avg_order_value', 0):,.2f}"],
        ["Unique customers", f"{a['uniqueCustomers']:,}"],
        ["Units sold", f"{k['units']:,}" if k.get("units") is not None else "n/a"],
    ]
    out = [_p("2. Key metrics", H1), _table(rows, [7 * cm, 6 * cm])]
    pc = k.get("period_change")
    if pc and pc.get("change_pct") is not None:
        out.append(
            _p(
                f"Revenue changed {pc['change_pct']:+.1f}% from {pc['previous_label']} (${pc['previous_revenue']:,.0f}) to "
                f"{pc['current_label']} (${pc['current_revenue']:,.0f}).",
                BODY,
            )
        )
    return out


def _sec_trend(a: dict, m: dict) -> list:
    bars = a["trendData"]
    fig, ax = plt.subplots(figsize=(7.5, 3))
    ax.bar([b["name"] for b in bars], [b["numericValue"] for b in bars], color=GREEN)
    ax.set_title(f"Revenue by {a.get('trendGranularity', 'period')} (headline {a['trendSummary']}, {a['trendBadge']})", fontsize=9)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.tick_params(labelsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return [
        _p("3. Revenue trend", H1),
        _chart(fig),
        _table([["Period", "Revenue"]] + [[b["name"], b["value"]] for b in bars], [5 * cm, 6 * cm]),
    ]


def _sec_insights(a: dict, m: dict) -> list:
    out = [_p("4. Insights", H1)]
    for i in a["insights"][:20]:
        out.append(_p(f"[{i['type']} / {i['severity']}] {i['title']}", H2))
        out.append(_p(i["desc"]))
        if i.get("recommendation"):
            out.append(_p(f"Recommendation: {i['recommendation']}", SMALL))
    return out


def _sec_forecast(a: dict, m: dict) -> list:
    out = [_p("5. Forecast", H1)]
    f = m.get("forecast")
    if not _usable(f):
        return out + _na("forecast", f)
    t = f["next_30_days"]
    out.append(
        _p(
            f"Next 30 days: about ${t['total']:,.0f} (90% range ${t['lower']:,.0f} to ${t['upper']:,.0f}). Winner: {f['winner']} "
            f"(sMAPE {f['winner_smape']:.1f}%, chosen by {f['cv']['folds']}-fold rolling-origin cross-validation on {f['cv']['history_days']} days)."
        )
    )
    if f["status"] == "unreliable":
        out.append(_p("Caution: " + f["reason"], NA))
    hist, fut = f["history_tail"], f["daily"]
    fig, ax = plt.subplots(figsize=(7.5, 3))
    ax.plot([h["date"] for h in hist], [h["value"] for h in hist], color=DARK, lw=1, label="actual")
    ax.plot([d["date"] for d in fut], [d["forecast"] for d in fut], color=GREEN, lw=1.5, label="forecast")
    ax.fill_between(
        [d["date"] for d in fut], [d["lower"] for d in fut], [d["upper"] for d in fut], color=GREEN, alpha=0.25, label="90% interval"
    )
    ax.set_xticks([h["date"] for h in hist][::15] + [d["date"] for d in fut][::10])
    ax.tick_params(labelsize=6, axis="x", rotation=45)
    ax.tick_params(labelsize=7, axis="y")
    ax.legend(fontsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    out += [
        _chart(fig),
        _p("Model leaderboard (lower sMAPE is better)", H2),
        _table(
            [["Model", "sMAPE %", "MAE", "Status"]] + [[b["model"], b["smape"], b["mae"], b["status"]] for b in f["leaderboard"]],
            [5 * cm, 3 * cm, 3 * cm, 5 * cm],
        ),
    ]
    return out


def _sec_anomalies(a: dict, m: dict) -> list:
    out = [_p("6. Anomalies and root causes", H1)]
    r = m.get("anomalies")
    if not _usable(r):
        return out + _na("anomalies", r)
    if not r["anomalies"]:
        return out + [_p(f"No unusual days in {r['days_analyzed']} days.")]
    out.append(_p(f"Method: {r['method']}."))
    out.append(
        _table(
            [["Date", "Type", "Revenue", "Expected", "Deviation", "Main cause"]]
            + [
                [
                    x["date"],
                    x["direction"],
                    _money(x["value"]),
                    _money(x["expected"]),
                    f"{x['deviation_pct']:+.0f}%" if x["deviation_pct"] is not None else "-",
                    x["cause_text"],
                ]
                for x in r["anomalies"][:10]
            ],
            [2.2 * cm, 1.5 * cm, 2.2 * cm, 2.2 * cm, 2 * cm, 6.5 * cm],
        )
    )
    return out


def _sec_customers(a: dict, m: dict) -> list:
    out = [_p("7. Customer segments and churn risk", H1)]
    s, c = m.get("segments"), m.get("churn")
    if not _usable(s):
        out += _na("segments", s)
    else:
        segs = s["segments"]
        fig, ax = plt.subplots(figsize=(7.5, 2.8))
        ax.barh([x["name"] for x in segs][::-1], [x["revenue_share_pct"] for x in segs][::-1], color=GREEN)
        ax.set_xlabel("% of revenue", fontsize=8)
        ax.tick_params(labelsize=8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        out += [
            _p(f"{s['customers']} customers in {s['k']} segments (K-Means, k chosen by silhouette).", BODY),
            _chart(fig),
            _table(
                [["Segment", "Customers", "Revenue share", "Avg recency (d)", "Avg orders", "Avg spend"]]
                + [
                    [
                        x["name"],
                        x["customers"],
                        f"{x['revenue_share_pct']}%",
                        x["avg_recency_days"],
                        x["avg_frequency"],
                        _money(x["avg_monetary"]),
                    ]
                    for x in segs
                ]
            ),
        ]
    out.append(_p("Churn risk", H2))
    if not _usable(c):
        return out + _na("churn", c)
    how = (
        f"{c['model']} (ROC-AUC {c['metrics']['roc_auc']:.2f}, precision {c['metrics']['precision']:.2f}, recall {c['metrics']['recall']:.2f})"
        if c["method"] == "model"
        else "transparent heuristic (too little data for a model)"
    )
    out.append(
        _p(
            f"{c['at_risk_customers']} of {c['active_customers']} active customers have a churn probability of at least 50% "
            f"({c['at_risk_revenue_share_pct']}% of historical revenue). Churn = no purchase within {c['window_days']} days "
            f"({c['window_rule']}). Method: {how}. {c['leakage_guard']}."
        )
    )
    out.append(
        _table(
            [["Customer", "Churn probability", "Days since last order", "Orders", "Lifetime spend"]]
            + [
                [t["customer"], f"{100 * t['churn_probability']:.0f}%", t["recency_days"], t["frequency"], _money(t["monetary"])]
                for t in c["top_at_risk"]
            ]
        )
    )
    return out


def _sec_drivers(a: dict, m: dict) -> list:
    out = [_p("8. Why did revenue change?", H1)]
    d = m.get("drivers")
    if not _usable(d):
        return out + _na("drivers", d)
    e = d["effects"]
    out.append(
        _p(
            f"Revenue moved {d['change_pct']:+.1f}% from ${d['revenue_previous']:,.0f} ({d['previous_label']}) to "
            f"${d['revenue_current']:,.0f} ({d['current_label']}). Exact decomposition: price {e['price']:+,.0f}, volume {e['volume']:+,.0f}, "
            f"mix {e['mix']:+,.0f}; these sum to the total change (reconciles: {d['reconciles']})."
        )
    )
    out.append(
        _table(
            [["Segment", "Change", "Points of total", "Price", "Volume", "Mix"]]
            + [
                [
                    x["segment"],
                    f"{x['delta']:+,.0f}",
                    f"{x['pts']:+.1f}",
                    f"{x['price_effect']:+,.0f}",
                    f"{x['volume_effect']:+,.0f}",
                    f"{x['mix_effect']:+,.0f}",
                ]
                for x in d["top_segments"]
            ]
        )
    )
    ml = d["ml_explanation"]
    if ml["status"] == "ok":
        out.append(
            _p(
                f"ML explanation ({ml['model']}, hold-out R^2 {ml['holdout_r2']:.2f}, quality: {ml['model_quality']}). "
                + (ml.get("note", ""))
            )
        )
        out.append(
            _table(
                [["Factor", "Effect on daily revenue", "Direction"]]
                + [[f["label"], f"{f['effect_per_day']:+,.0f}", f["direction"]] for f in ml["factors"]]
            )
        )
    else:
        out += _na("drivers (ML explanation)", ml)
    return out


def _sec_pricing(a: dict, m: dict) -> list:
    out = [_p("9. Price elasticity", H1)]
    p = m.get("pricing")
    if p is None or p.get("status") == "skipped":
        return out + _na("pricing", p)
    out.append(_p(f"{p['method']}. Segments by {p['segment_dimension']}. Simulator changes are limited to +-{p['max_change_pct']:.0f}%."))
    rows = [["Segment", "Elasticity", "95% CI", "p-value", "Reliability", "Best move"]]
    for s in p["segments"]:
        if s["reliability"] == "reliable":
            bm = s["best_move"]
            rows.append(
                [
                    s["segment"],
                    s["elasticity"],
                    f"{s['ci_low']} to {s['ci_high']}",
                    s["p_value"],
                    "reliable",
                    f"{bm['price_change_pct']:+.0f}% ({bm['optimises']} {bm['expected_gain']:+,.0f})",
                ]
            )
        else:
            rows.append([s["segment"], s.get("elasticity", "-"), "-", s.get("p_value", "-"), s["reliability"], s["reason"][:70]])
    return out + [_table(rows)]


def _sec_basket(a: dict, m: dict) -> list:
    out = [_p("10. Cross-sell rules", H1)]
    b = m.get("basket")
    if not _usable(b) or not b.get("rules"):
        return out + _na("basket", b)
    out.append(_p(f"{b['multi_item_baskets']} multi-item baskets (basis: {b['basket_basis']}, items: {b['item_level']})."))
    return out + [
        _table(
            [["If a customer buys", "also buys", "Lift", "Confidence", "Orders"]]
            + [[r["antecedent"], r["consequent"], r["lift"], f"{100 * r['confidence']:.0f}%", r["co_occurrences"]] for r in b["rules"]]
        )
    ]


def _sec_docs(a: dict, m: dict, docs: list[dict], cited: list[str]) -> list:
    out = [_p("11. Documents", H1)]
    if not docs and not cited:
        return out + [_p("No documents are indexed for this account.")]
    if docs:
        out.append(_p("Indexed documents available to the assistant:"))
        out.append(
            _table([["File", "Scope", "Passages"]] + [[d["fileName"], "shared" if d["shared"] else d["scope"], d["chunks"]] for d in docs])
        )
    out.append(_p("Documents cited in this dataset's chat: " + (", ".join(cited) if cited else "none yet.")))
    return out


def build_report(
    dataset_name: str, analytics: dict, modules: dict, docs: list[dict] | None = None, cited: list[str] | None = None
) -> bytes:
    """Render the report. ``modules`` is the stored per-module output; ``docs`` the indexed documents."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Business Insight Report - {dataset_name}",
        author="Business Insight Platform",
    )
    q = analytics.get("quality") or {}
    flow: list = [
        Spacer(1, 3 * cm),
        _p("Business Insight Report", ParagraphStyle("T", parent=H1, fontSize=26, leading=30)),
        _p(f"Dataset: {dataset_name}", H2),
        _p(
            f"Generated {datetime.now():%Y-%m-%d %H:%M} | {analytics['recordsCount']:,} records | "
            f"{' to '.join(q.get('date_range', ['?', '?']))} | all analysis computed locally",
            SMALL,
        ),
        Spacer(1, 1 * cm),
    ]
    skipped = [k for k in ("forecast", "anomalies", "segments", "churn", "drivers", "pricing", "basket") if not _usable(modules.get(k))]
    flow.append(_p("Not available in this report: " + (", ".join(skipped) if skipped else "none (every module produced results)"), SMALL))
    flow.append(PageBreak())
    sections = [
        _sec_quality,
        _sec_kpis,
        _sec_trend,
        _sec_insights,
        _sec_forecast,
        _sec_anomalies,
        _sec_customers,
        _sec_drivers,
        _sec_pricing,
        _sec_basket,
    ]
    for fn in sections:
        try:
            flow += fn(analytics, modules)
        except Exception as exc:  # noqa: BLE001 - one broken section must not break the whole report
            log.exception("Report section %s failed", fn.__name__)
            flow += [
                _p(fn.__name__.replace("_sec_", "").title(), H1),
                _p(f"Not available: this section could not be rendered ({type(exc).__name__}).", NA),
            ]
        flow.append(Spacer(1, 10))
    try:
        flow += _sec_docs(analytics, modules, docs or [], cited or [])
    except Exception:  # noqa: BLE001
        log.exception("Report documents section failed")

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(GREY))
        canvas.drawString(1.8 * cm, 1 * cm, f"Business Insight Platform - {dataset_name}")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1 * cm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
