"""LLM narrative insights, strictly grounded in computed facts.

Flow: facts (dict) -> Ollama writes 3-5 JSON insights -> **number-grounding check** drops any sentence
containing a number that is not in the facts -> if the LLM is unavailable, times out, or too little
survives, deterministic template insights are produced from the same facts.

Dataset text (product/region/customer names) is untrusted: it is sanitised, passed only as JSON data,
and the prompt forbids following instructions inside it. Output containing injection markers is dropped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from ..llm import ollama_client
from ..llm.ollama_client import LLMUnavailable

PROMPT_DIR = Path(__file__).resolve().parent.parent / "llm" / "prompts"
VALID_TYPES = {"growth", "alert", "opportunity", "info"}
_NUM = re.compile(r"(?<![\w.])\$?(\d[\d,]*(?:\.\d+)?)\s*(%|[kKmMbB]\b)?")
_SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9}
_BAD_OUTPUT = re.compile(r"https?://|```|ignore (all |any )?(previous|prior)|system prompt|as an ai", re.I)


def clean_text(value: object, limit: int = 40) -> str:
    """Sanitise untrusted dataset text before it enters a prompt."""
    s = re.sub(r"[\x00-\x1f\x7f{}<>`\\]", " ", str(value))
    return re.sub(r"\s+", " ", s).strip()[:limit]


# ----------------------------------------------------------------------------- facts
def _top(df: pd.DataFrame, col: str, n: int = 3) -> list[dict]:
    g = df.groupby(col)["revenue"].sum().sort_values(ascending=False)
    tot = float(g.sum()) or 1.0
    return [{"name": clean_text(k), "revenue": round(float(v)), "share_pct": round(100 * float(v) / tot, 1)} for k, v in g.head(n).items()]


def build_facts(df: pd.DataFrame, analytics: dict, modules: dict) -> dict:
    """Compact, JSON-serialisable facts the narrative may use. Nothing else is allowed in the text."""
    kp = analytics.get("kpis") or {}
    facts: dict = {
        "file": clean_text(analytics.get("fileName", "")),
        "date_range": (analytics.get("quality") or {}).get("date_range"),
        "totals": {
            "revenue": round(analytics["revenue"]),
            "orders": analytics["orders"],
            "customers": analytics["uniqueCustomers"],
            "avg_order_value": round(kp.get("avg_order_value", 0), 2),
        },
    }
    if kp.get("has_cost"):
        facts["totals"].update(profit=round(analytics["totalProfit"]), margin_pct=round(analytics["profitMargin"], 1))
    pc = kp.get("period_change")
    if pc and pc.get("change_pct") is not None:
        facts["period_change"] = {
            "current": pc["current_label"],
            "previous": pc["previous_label"],
            "change_pct": pc["change_pct"],
            "current_revenue": round(pc["current_revenue"]),
            "previous_revenue": round(pc["previous_revenue"]),
        }
    for col, key in (("category", "top_categories"), ("region", "top_regions"), ("product", "top_products")):
        if col in df:
            facts[key] = _top(df, col)
    item = "product" if "product" in df else ("category" if "category" in df else None)
    if item and "cost" in df:
        g = df.groupby(item).agg(r=("revenue", "sum"), c=("cost", "sum"))
        g = g[g["r"] >= 0.01 * g["r"].sum()]
        if len(g):
            g["m"] = 100 * (g["r"] - g["c"]) / g["r"]
            lo = g["m"].idxmin()
            facts["lowest_margin"] = {"name": clean_text(lo), "margin_pct": round(float(g.loc[lo, "m"]), 1)}
    fc = modules.get("forecast") or {}
    if fc.get("status") in ("ok", "unreliable"):
        t = fc["next_30_days"]
        facts["forecast"] = {
            "horizon_days": fc["horizon_days"],
            "next_30_days": round(t["total"]),
            "range_low": round(t["lower"]),
            "range_high": round(t["upper"]),
            "model": fc["winner"],
            "smape_pct": fc["winner_smape"],
        }
    an = modules.get("anomalies") or {}
    if an.get("status") == "ok" and an["anomalies"]:
        facts["anomalies"] = [
            {"date": a["date"], "direction": a["direction"], "deviation_pct": a["deviation_pct"], "cause": clean_text(a["cause_text"], 90)}
            for a in an["anomalies"][:2]
        ]
    seg = modules.get("segments") or {}
    if seg.get("status") == "ok":
        facts["customer_segments"] = [
            {"name": x["name"], "customers": x["customers"], "revenue_share_pct": x["revenue_share_pct"]} for x in seg["segments"][:3]
        ]
    ch = modules.get("churn") or {}
    if ch.get("status") in ("ok", "unreliable") and ch.get("at_risk_customers"):
        facts["churn"] = {
            "at_risk_customers": ch["at_risk_customers"],
            "at_risk_revenue_share_pct": ch["at_risk_revenue_share_pct"],
            "window_days": ch["window_days"],
        }
    dr = modules.get("drivers") or {}
    if dr.get("status") == "ok":
        from ..ml.drivers import main_driver

        top, offset = main_driver(dr)
        facts["revenue_driver"] = {"segment": clean_text(top["segment"]), "pts": top["pts"], "change_pct": dr["change_pct"]}
        if offset:
            facts["revenue_driver"]["largest_offset"] = {"segment": clean_text(offset["segment"]), "pts": offset["pts"]}
    pr = modules.get("pricing") or {}
    rel = [e for e in pr.get("segments", []) if e["reliability"] == "reliable" and e["segment"] != "All"]
    if rel:
        facts["pricing"] = [{"segment": clean_text(e["segment"]), "elasticity": e["elasticity"]} for e in rel[:2]]
    bk = modules.get("basket") or {}
    if bk.get("rules"):
        r = bk["rules"][0]
        facts["cross_sell"] = {
            "if_buys": clean_text(r["antecedent"]),
            "also_buys": clean_text(r["consequent"]),
            "lift": r["lift"],
            "confidence_pct": round(100 * r["confidence"], 1),
        }
    return facts


# ----------------------------------------------------------------------------- grounding
def _numbers(text: str) -> list[tuple[float, bool, float]]:
    """``(value, is_marked, rounding_tolerance)`` for each number in ``text``.

    ``is_marked`` = has %, $ or a K/M/B suffix. The tolerance is half a unit of the last displayed
    digit (so ``$1.2M`` may stand for anything within 0.05M, and ``28%`` for 27.5-28.5).
    """
    out = []
    for m in _NUM.finditer(text):
        raw, suf = m.group(1).replace(",", ""), m.group(2)
        try:
            val = float(raw)
        except ValueError:
            continue
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        mult = _SUFFIX.get(suf.lower(), 1.0) if suf else 1.0
        out.append((val * mult, bool(suf) or m.group(0).startswith("$"), 0.5 * 10 ** (-decimals) * mult))
    return out


def allowed_numbers(facts: dict) -> list[float]:
    return [v for v, _, _ in _numbers(json.dumps(facts, ensure_ascii=False))]


def is_grounded(text: str, allowed: list[float]) -> bool:
    """True if every number in ``text`` appears in the facts (within 0.5% or its own rounding precision).

    Bare integers 0-5 (counting words like "top 3") are tolerated; anything with %, $ or a K/M suffix is not.
    """
    for val, marked, tol in _numbers(text):
        if not marked and float(val).is_integer() and 0 <= val <= 5:
            continue
        if not any(abs(val - a) <= max(0.005 * abs(a), tol) for a in allowed):
            return False
    return True


def ground_insight(item: dict, allowed: list[float]) -> tuple[dict | None, int]:
    """Return (cleaned insight or None, number of dropped sentences)."""
    title = clean_text(item.get("title", ""), 90)
    if not title or _BAD_OUTPUT.search(json.dumps(item)) or not is_grounded(title, allowed):
        return None, 1
    dropped = 0

    def keep(text: str) -> str:
        nonlocal dropped
        kept = []
        for s in re.split(r"(?<=[.!?])\s+", str(text).strip()):
            if not s:
                continue
            if is_grounded(s, allowed):
                kept.append(s)
            else:
                dropped += 1
        return " ".join(kept)

    desc, rec = keep(item.get("desc", "")), keep(item.get("recommendation", ""))
    if not desc:
        return None, dropped
    t = item.get("type") if item.get("type") in VALID_TYPES else "info"
    return {"title": title, "desc": desc, "recommendation": rec or "Review this finding with your team.", "type": t}, dropped


# ----------------------------------------------------------------------------- fallback
def template_insights(facts: dict) -> list[dict]:
    """Deterministic insights written from the facts (used when the LLM is unavailable)."""
    out: list[dict] = []
    tc = facts.get("top_categories") or []
    if tc:
        out.append(
            {
                "title": f"Summary: {tc[0]['name']} is the top category ({tc[0]['share_pct']}% of revenue)",
                "desc": f"{tc[0]['name']} generated ${tc[0]['revenue']:,} of ${facts['totals']['revenue']:,} total revenue.",
                "recommendation": "Protect stock and marketing for this category; look for ways to lift the weaker ones.",
                "type": "opportunity",
            }
        )
    tr = facts.get("top_regions") or []
    if tr:
        out.append(
            {
                "title": f"Summary: {tr[0]['name']} is the strongest region ({tr[0]['share_pct']}%)",
                "desc": f"{tr[0]['name']} brought in ${tr[0]['revenue']:,}, the largest regional share of revenue.",
                "recommendation": "Study what works in this region and replicate it elsewhere.",
                "type": "info",
            }
        )
    t = facts["totals"]
    if "margin_pct" in t:
        low = facts.get("lowest_margin")
        extra = f" The lowest-margin line is {low['name']} at {low['margin_pct']}%." if low else ""
        out.append(
            {
                "title": f"Summary: overall profit margin is {t['margin_pct']}%",
                "desc": (
                    f"Profit is ${t['profit']:,} on ${t['revenue']:,} revenue."
                    if "profit" in t
                    else f"Margin is {t['margin_pct']}% on ${t['revenue']:,} revenue."
                )
                + extra,
                "recommendation": "Review pricing and supplier costs on the lowest-margin lines.",
                "type": "alert" if t["margin_pct"] < 15 else "info",
            }
        )
    pc = facts.get("period_change")
    if pc:
        up = pc["change_pct"] >= 0
        out.append(
            {
                "title": f"Summary: revenue {'rose' if up else 'fell'} {abs(pc['change_pct'])}% in {pc['current']}",
                "desc": f"Revenue moved from ${pc['previous_revenue']:,} in {pc['previous']} to ${pc['current_revenue']:,} in {pc['current']}.",
                "recommendation": "Identify what changed (see Revenue Drivers) and act on it.",
                "type": "growth" if up else "alert",
            }
        )
    fc = facts.get("forecast")
    if fc:
        out.append(
            {
                "title": f"Summary: expect about ${fc['next_30_days']:,} over the next 30 days",
                "desc": f"The {fc['model']} model projects ${fc['next_30_days']:,} (range ${fc['range_low']:,} to ${fc['range_high']:,}).",
                "recommendation": "Plan around the range rather than a single number.",
                "type": "info",
            }
        )
    return out[:5]


def _system_prompt() -> str:
    return (PROMPT_DIR / "narrative_system.txt").read_text()


def _user_prompt(facts: dict) -> str:
    return (PROMPT_DIR / "narrative_user.txt").read_text().replace("{facts}", json.dumps(facts, ensure_ascii=False))


def make_narrative(facts: dict) -> dict:
    """Return ``{status, source, reason?, insights: [...], dropped_sentences}``."""
    allowed = allowed_numbers(facts)
    reason = ""
    try:
        if not ollama_client.is_available():
            raise LLMUnavailable("Ollama is not running or the model is not installed.")
        data = ollama_client.generate_json(_system_prompt(), _user_prompt(facts), timeout=90)
        raw = data.get("insights", []) if isinstance(data, dict) else []
        good, dropped = [], 0
        for it in raw[:5]:
            if not isinstance(it, dict):
                continue
            g, d = ground_insight(it, allowed)
            dropped += d
            if g:
                good.append(g)
        if len(good) >= 2:
            return {"status": "ok", "source": "llm", "insights": good, "dropped_sentences": dropped}
        reason = f"Too few grounded LLM insights survived the number check ({len(good)})."
    except LLMUnavailable as exc:
        reason = str(exc)
    return {"status": "ok", "source": "template", "reason": reason, "insights": template_insights(facts), "dropped_sentences": 0}
