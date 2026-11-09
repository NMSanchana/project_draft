"""KPI computation and period selection."""

from __future__ import annotations

import pandas as pd


def _month_is_full(df_dates: pd.Series, month: pd.Period, tol_days: int = 2) -> bool:
    start, end = month.start_time.normalize(), month.end_time.normalize()
    return df_dates.min() <= start + pd.Timedelta(days=tol_days) and df_dates.max() >= end - pd.Timedelta(days=tol_days)


def last_full_months(dates: pd.Series) -> tuple[pd.Period, pd.Period] | None:
    """The two latest *consecutive, fully covered* calendar months in the data, or None."""
    months = sorted(dates.dt.to_period("M").unique())
    full = [m for m in months if _month_is_full(dates, m)]
    for cur, prev in zip(reversed(full), reversed(full[:-1])):
        if (cur - prev).n == 1:
            return cur, prev
    return None


def period_comparison(df: pd.DataFrame) -> dict | None:
    """Compare the last full month with the one before; fall back to first/second half of the data.

    Returns ``{basis, current, previous, current_label, previous_label, current_revenue,
    previous_revenue, change_pct, current_mask, previous_mask}`` or None when impossible.
    """
    if df.empty:
        return None
    pair = last_full_months(df["date"])
    if pair:
        cur, prev = pair
        m = df["date"].dt.to_period("M")
        cur_mask, prev_mask = m == cur, m == prev
        basis, cl, pl = "month", cur.strftime("%B %Y"), prev.strftime("%B %Y")
    else:
        lo, hi = df["date"].min(), df["date"].max()
        if lo == hi:
            return None
        mid = lo + (hi - lo) / 2
        cur_mask, prev_mask = df["date"] > mid, df["date"] <= mid
        basis, cl, pl = "half", "second half of the data", "first half of the data"
    cur_rev, prev_rev = float(df.loc[cur_mask, "revenue"].sum()), float(df.loc[prev_mask, "revenue"].sum())
    change = None if prev_rev <= 0 else round(100 * (cur_rev - prev_rev) / prev_rev, 2)
    return {
        "basis": basis,
        "current_label": cl,
        "previous_label": pl,
        "current_revenue": round(cur_rev, 2),
        "previous_revenue": round(prev_rev, 2),
        "change_pct": change,
        "current_mask": cur_mask,
        "previous_mask": prev_mask,
    }


def compute_kpis(df: pd.DataFrame) -> dict:
    """Headline KPIs from the canonical frame."""
    revenue = float(df["revenue"].sum())
    has_cost = "cost" in df
    cost = float(df["cost"].sum()) if has_cost else 0.0
    profit = revenue - cost if has_cost else 0.0
    orders = int(df["order_id"].nunique()) if "order_id" in df else int(len(df))
    cmp = period_comparison(df)
    return {
        "revenue": round(revenue, 2),
        "total_cost": round(cost, 2),
        "total_profit": round(profit, 2),
        "profit_margin_pct": round(100 * profit / revenue, 2) if has_cost and revenue > 0 else 0.0,
        "has_cost": has_cost,
        "orders": orders,
        "avg_order_value": round(revenue / orders, 2) if orders else 0.0,
        "unique_customers": int(df["customer"].nunique()) if "customer" in df else 0,
        "units": int(df["quantity"].sum()) if "quantity" in df else None,
        "rows": int(len(df)),
        "period_change": None if cmp is None else {k: v for k, v in cmp.items() if not k.endswith("_mask")},
    }
