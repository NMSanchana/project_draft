"""Plain-text answers from ML module output (numbers copied from module results; nothing invented)."""

from __future__ import annotations

import re

import pandas as pd

from ..ml import drivers as drivers_mod
from ..ml import pricing as pricing_mod
from ..ml.drivers import signed_money
from . import timeparse

CAUTION_HEAD = {
    "pending": "That analysis is still running; ask again in a few seconds.",
    "failed": "That analysis failed for this dataset.",
}


def _gate(res: dict | None, name: str) -> str | None:
    """Return an explanatory message when the module has no usable result."""
    if res is None:
        return f"The {name} analysis isn't available for this dataset."
    if res.get("status") in CAUTION_HEAD:
        return CAUTION_HEAD[res["status"]] + (f" ({res['reason']})" if res.get("reason") else "")
    if res.get("status") == "skipped":
        return f"I couldn't run the {name} analysis: {res.get('reason', 'not enough data')}"
    return None


def _forecast(m: dict, message: str) -> str:
    f = m.get("forecast")
    if g := _gate(f, "forecast"):
        return g
    t = f["next_30_days"]
    out = (
        f"Projected revenue for the next 30 days is about ${t['total']:,.0f} (90% range ${t['lower']:,.0f} to ${t['upper']:,.0f}).\n"
        f"Next 7 days: about ${f['next_7_days']:,.0f}. Best model: {f['winner']} (sMAPE {f['winner_smape']:.1f}%)."
    )
    if f.get("projected_change_pct") is not None:
        out += f"\nThat is {f['projected_change_pct']:+.1f}% versus the last 30 days."
    if f["status"] == "unreliable":
        out += "\nCaution: " + f["reason"]
    return out


def _anomalies(m: dict, message: str) -> str:
    a = m.get("anomalies")
    if g := _gate(a, "anomaly"):
        return g
    if not a["anomalies"]:
        return f"No unusual days found in {a['days_analyzed']} days of data."
    lines = [f"Found {a['count']} unusual day(s):"]
    for x in a["anomalies"][:3]:
        pct = f" ({x['deviation_pct']:+.0f}%)" if x["deviation_pct"] is not None else ""
        lines.append(f"{x['date']}: {x['direction']}{pct}, ${x['value']:,.0f} vs about ${x['expected']:,.0f}. {x['cause_text']}.")
    return "\n".join(lines)


def _segments(m: dict, message: str) -> str:
    s = m.get("segments")
    if g := _gate(s, "customer segmentation"):
        return g
    lines = [f"Your {s['customers']} customers fall into {s['k']} segments:"]
    lines += [f"{x['name']}: {x['customers']} customers, {x['revenue_share_pct']:.0f}% of revenue" for x in s["segments"][:5]]
    return "\n".join(lines)


def _churn(m: dict, message: str) -> str:
    c = m.get("churn")
    if g := _gate(c, "churn"):
        return g
    how = (
        f"{c['model']}, ROC-AUC {c['metrics']['roc_auc']:.2f}"
        if c["method"] == "model"
        else "simple heuristic, too little data for a model"
    )
    out = (
        f"{c['at_risk_customers']} of {c['active_customers']} active customers are likely to lapse "
        f"({c['at_risk_revenue_share_pct']:.0f}% of historical revenue; {how}). Churn = no purchase in {c['window_days']} days."
    )
    top = ", ".join(f"{t['customer']} ({100 * t['churn_probability']:.0f}%)" for t in c["top_at_risk"][:3])
    return out + (f"\nHighest risk: {top}." if top else "")


def _basket(m: dict, message: str) -> str:
    b = m.get("basket")
    if g := _gate(b, "cross-sell"):
        return g
    if not b.get("rules"):
        return b.get("reason", "No reliable cross-sell rules were found.")
    lines = ["Products bought together most often:"]
    lines += [
        f"{r['antecedent']} -> {r['consequent']}: lift {r['lift']:.1f}, confidence {100 * r['confidence']:.0f}% ({r['co_occurrences']} orders)"
        for r in b["rules"][:3]
    ]
    return "\n".join(lines)


def _month_range(period: str) -> tuple[str, str]:
    p = pd.Period(period)
    return p.start_time.strftime("%Y-%m-%d"), p.end_time.strftime("%Y-%m-%d")


def _drivers(m: dict, message: str, df: pd.DataFrame | None) -> str:
    res = m.get("drivers")
    if df is not None:
        months = timeparse.months_in(message, df["date"])
        if months:
            cur = months[0]
            prev = months[1] if len(months) > 1 else str(pd.Period(cur) - 1)
            res = drivers_mod.run_drivers(df, _month_range(cur), _month_range(prev))
    if g := _gate(res, "revenue drivers"):
        return g
    word = "rose" if res["change_pct"] >= 0 else "fell"
    driver, offset = drivers_mod.main_driver(res)
    e = res["effects"]
    out = (
        f"Revenue {word} {abs(res['change_pct']):.1f}% from ${res['revenue_previous']:,.0f} ({res['previous_label']}) "
        f"to ${res['revenue_current']:,.0f} ({res['current_label']}).\n"
        f"Driven mainly by {driver['segment']} ({driver['pts']:+.1f} pts)"
        + (f", partly offset by {offset['segment']} ({offset['pts']:+.1f} pts)." if offset else ".")
        + f"\nPrice effect {signed_money(e['price'])}, volume {signed_money(e['volume'])}, mix {signed_money(e['mix'])} (these sum exactly to the change)."
    )
    ml = res["ml_explanation"]
    if ml["status"] == "ok" and ml["model_quality"] == "good" and ml["factors"]:
        f = ml["factors"][0]
        out += f"\nML check (R^2 {ml['holdout_r2']:.2f}): biggest factor is {f['label']} ({f['direction']})."
    return out


def _pricing(m: dict, message: str) -> str:
    p = m.get("pricing")
    if g := _gate(p, "pricing"):
        return g
    names = {s["segment"].lower(): s["segment"] for s in p["segments"]}
    seg = next(
        (names[k] for k in sorted(names, key=len, reverse=True) if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", message.lower())), None
    )
    mt = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(%|percent)", message.lower())
    if seg is None and not mt:
        rel = [s for s in p["segments"] if s["reliability"] == "reliable" and s["segment"] != "All"] or [
            s for s in p["segments"] if s["reliability"] == "reliable"
        ]
        if not rel:
            return "I couldn't measure price sensitivity reliably: " + p.get("reason", "prices barely vary in this data.")
        return "Price elasticity (reliable segments):\n" + "\n".join(
            f"{s['segment']}: {s['elasticity']:.2f} ({s['class']})" for s in rel[:5]
        )
    pct = float(mt.group(1)) if mt else 5.0
    if re.search(r"lower|reduce|cut|decrease|drop|discount", message.lower()) and pct > 0:
        pct = -pct
    if abs(pct) > pricing_mod.MAX_CHANGE_PCT:
        return f"I can only simulate price changes within ±{pricing_mod.MAX_CHANGE_PCT:.0f}%."
    sim = pricing_mod.simulate(p, seg or "All", pct)
    if not sim["reliable"]:
        return sim["message"]
    lines = [
        f"If you change {sim['segment']} prices by {pct:+.0f}% (elasticity {sim['elasticity']:.2f}): units {sim['units_change_pct']:+.1f}%, "
        f"revenue {sim['revenue_delta']:+,.0f} (range {sim['revenue_delta_range'][0]:+,.0f} to {sim['revenue_delta_range'][1]:+,.0f})."
    ]
    if sim["profit_delta"] is not None:
        lines.append(
            f"Profit {sim['profit_delta']:+,.0f} (range {sim['profit_delta_range'][0]:+,.0f} to {sim['profit_delta_range'][1]:+,.0f})."
        )
    if sim.get("recommended"):
        r = sim["recommended"]
        lines.append(f"Best {r['optimises']} move within ±20%: {r['price_change_pct']:+.0f}% (about {r['expected_gain']:+,.0f}).")
    return "\n".join(lines)


def answer_ml(module: str, message: str, modules: dict, df: pd.DataFrame | None, dataset_status: str) -> str:
    """Build the plain-text answer for an ML intent."""
    if dataset_status == "failed":
        return "The analysis of this dataset failed, so I can't answer that."
    handlers = {
        "forecast": _forecast,
        "anomalies": _anomalies,
        "segments": _segments,
        "churn": _churn,
        "basket": _basket,
        "pricing": _pricing,
    }
    if module == "drivers":
        return _drivers(modules, message, df)
    pending = dataset_status == "enriching" and modules.get(module) is None
    if pending:
        return CAUTION_HEAD["pending"]
    return handlers[module](modules, message)
