"""Whitelisted pandas executor: the ONLY code that touches the dataframe, and it runs validated plans only.

No ``eval``/``exec``, no model-generated code. Every number in a data answer comes from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import timeparse
from .plan import METRIC_KIND, METRIC_LABEL, QueryPlan, TimeRange

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class ExecResult:
    plan: QueryPlan
    ok: bool = True
    error: str | None = None
    value: float | None = None  # total / compare (current period)
    previous: float | None = None  # compare only
    rows: list[dict] = field(default_factory=list)  # group / trend: [{"label", "value"}]
    n_rows: int = 0  # dataset rows the plan used
    scope: str = ""  # human description of filters + period
    detail: dict = field(default_factory=dict)

    @property
    def kind(self) -> str:
        return METRIC_KIND[self.plan.metric]

    @property
    def label(self) -> str:
        return METRIC_LABEL[self.plan.metric]


def _scope(plan: QueryPlan, tr: TimeRange | None) -> str:
    parts = [f.value for f in plan.filters]
    t = timeparse.describe(tr)
    return " ".join(x for x in [", ".join(parts), ("in " + t) if t else ""] if x)


def _need(plan: QueryPlan, df: pd.DataFrame) -> str | None:
    m = plan.metric
    if m in ("cost", "profit", "margin_pct") and "cost" not in df:
        return "This dataset has no cost or profit data, so I can't calculate that."
    if m in ("quantity", "avg_price") and "quantity" not in df:
        return "This dataset has no quantity column, so I can't calculate units or average price."
    if m == "customers" and "customer" not in df:
        return "This dataset has no customer column, so I can't count customers."
    return None


def _apply(df: pd.DataFrame, plan: QueryPlan, tr: TimeRange | None) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for f in plan.filters:
        mask &= df[f.column].astype(str).str.lower() == f.value.lower()
    if tr is not None and not tr.is_empty():
        mask &= timeparse.range_mask(df["date"], tr)
    return df[mask]


def _parts(sub: pd.DataFrame, keys=None) -> pd.DataFrame:
    """Additive building blocks per group (or one row when ``keys`` is None)."""
    t = sub.assign(_one=1)
    spec = {"R": ("revenue", "sum"), "rows": ("_one", "sum")}
    if "cost" in t:
        spec["C"] = ("cost", "sum")
    if "quantity" in t:
        spec["Q"] = ("quantity", "sum")
    if "order_id" in t:
        spec["O"] = ("order_id", "nunique")
    if "customer" in t:
        spec["U"] = ("customer", "nunique")
    if keys is None:
        return t.groupby(lambda _: 0).agg(**spec)
    return t.groupby(keys, observed=True).agg(**spec)


def _metric(p: pd.DataFrame, metric: str) -> pd.Series:
    R = p["R"]
    orders = p["O"] if "O" in p else p["rows"]
    with np.errstate(divide="ignore", invalid="ignore"):
        out = {
            "revenue": R,
            "cost": p.get("C"),
            "profit": R - p["C"] if "C" in p else None,
            "quantity": p.get("Q"),
            "orders": orders,
            "customers": p.get("U"),
            "aov": R / orders,
            "margin_pct": 100 * (R - p["C"]) / R if "C" in p else None,
            "avg_price": R / p["Q"] if "Q" in p else None,
        }[metric]
    return out.replace([np.inf, -np.inf], np.nan)


def _group_key(sub: pd.DataFrame, by: str) -> pd.Series:
    d = sub["date"]
    if by == "month":
        return d.dt.to_period("M").astype(str)
    if by == "week":
        return d.dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    if by == "day":
        return d.dt.strftime("%Y-%m-%d")
    if by == "weekday":
        return d.dt.dayofweek.map(dict(enumerate(WEEKDAYS)))
    return sub[by].astype(str)


def _single(sub: pd.DataFrame, plan: QueryPlan) -> float:
    return float(_metric(_parts(sub), plan.metric).iloc[0])


def run_plan(plan: QueryPlan, df: pd.DataFrame) -> ExecResult:
    """Execute a validated plan. Returns an ``ExecResult`` (``ok=False`` + friendly ``error`` when impossible)."""
    err = _need(plan, df)
    if err:
        return ExecResult(plan, ok=False, error=err)
    if plan.group_by in ("category", "region", "product", "customer", "status") and plan.group_by not in df:
        return ExecResult(plan, ok=False, error=f"This dataset has no {plan.group_by} column.")
    tr = plan.time_range
    sub = _apply(df, plan, tr)
    scope = _scope(plan, tr)
    if sub.empty:
        lo, hi = df["date"].min().strftime("%Y-%m-%d"), df["date"].max().strftime("%Y-%m-%d")
        return ExecResult(
            plan, ok=False, scope=scope, error=f"There is no data{(' for ' + scope) if scope else ''}. The dataset covers {lo} to {hi}."
        )

    if plan.operation == "compare":
        cr = plan.compare_range
        if cr is None:
            return ExecResult(plan, ok=False, error='Tell me which two periods to compare, e.g. "compare March and February".')
        prev = _apply(df, plan, cr)
        if prev.empty:
            return ExecResult(plan, ok=False, error=f"There is no data for {timeparse.describe(cr)} to compare with.")
        cur_v, prev_v = _single(sub, plan), _single(prev, plan)
        return ExecResult(
            plan,
            value=round(cur_v, 2),
            previous=round(prev_v, 2),
            n_rows=len(sub) + len(prev),
            scope=_scope(plan, tr),
            detail={"current_label": timeparse.describe(tr), "previous_label": timeparse.describe(cr)},
        )

    if plan.group_by is None or plan.operation == "total":
        v = _single(sub, plan)
        if not np.isfinite(v):
            return ExecResult(plan, ok=False, scope=scope, error="That figure can't be calculated for this selection (division by zero).")
        return ExecResult(plan, value=round(v, 2), n_rows=len(sub), scope=scope)

    keys = _group_key(sub, plan.group_by)
    series = _metric(_parts(sub, keys), plan.metric).dropna()
    if plan.group_by in ("month", "week", "day"):
        series = series.sort_index()
    elif plan.group_by == "weekday":
        series = series.reindex([w for w in WEEKDAYS if w in series.index])
    else:
        series = series.sort_values(ascending=(plan.sort == "asc"), kind="stable").head(plan.top_n)
    rows = [{"label": str(k), "value": round(float(v), 2)} for k, v in series.items()]
    return ExecResult(plan, rows=rows, n_rows=len(sub), scope=scope, detail={"groups_total": int(keys.nunique())})
