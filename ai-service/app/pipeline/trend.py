"""Revenue trend bars in the exact shape ``TrendChart.tsx`` consumes.

* ``heightPercent`` -> string like ``"73%"`` (relative to the tallest bar, min 6% for non-zero bars)
* ``value``         -> tooltip text like ``"$12,345"`` (same ``$`` style the KPI cards use)
* ``color``         -> Tailwind classes that already exist in the frontend source (Tailwind only
                       generates classes it finds in source): ``bg-[#54bd95]`` / ``bg-emerald-500``
* ``defaultActive`` -> the peak bar shows its tooltip by default
"""

from __future__ import annotations

import pandas as pd

from .kpis import _month_is_full

MAX_BARS = 8
COLOR_NORMAL = "bg-[#54bd95]"
COLOR_PEAK = "bg-emerald-500"


def money(v: float) -> str:
    return f"${v:,.0f}"


def _bucket(df: pd.DataFrame) -> tuple[pd.Series, str]:
    """Return revenue per bucket (indexed by bucket start) and the granularity name."""
    dates = df["date"]
    n_months = (dates.max().to_period("M") - dates.min().to_period("M")).n + 1
    if n_months >= 3:
        s = df.groupby(dates.dt.to_period("M"))["revenue"].sum()
        s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"), fill_value=0.0)
        s.index = s.index.to_timestamp()
        return s, "month"
    if (dates.max() - dates.min()).days >= 21:
        s = df.set_index("date")["revenue"].resample("W-MON", label="left", closed="left").sum()
        return s, "week"
    return df.set_index("date")["revenue"].resample("D").sum(), "day"


def build_trend(df: pd.DataFrame, period_change_pct: float | None = None) -> dict:
    """Returns ``{trendData, trendSummary, trendBadge, granularity}``."""
    series, gran = _bucket(df)
    series = series.tail(MAX_BARS)
    multi_year = series.index.min().year != series.index.max().year
    peak = float(series.max()) if len(series) else 0.0
    peak_idx = int(series.values.argmax()) if len(series) else -1

    bars = []
    for i, (ts, val) in enumerate(series.items()):
        if gran == "month":
            name = ts.strftime("%b %y") if multi_year else ts.strftime("%b")
        else:
            name = f"{ts.strftime('%b')} {ts.day}"
        partial = gran == "month" and not _month_is_full(df["date"], ts.to_period("M"))
        pct = 0.0 if peak <= 0 or val <= 0 else max(6.0, 100 * float(val) / peak)
        bars.append(
            {
                "name": name,
                "heightPercent": f"{pct:.0f}%",
                "value": money(float(val)) + (" (partial month)" if partial else ""),
                "numericValue": round(float(val), 2),
                "color": COLOR_PEAK if i == peak_idx else COLOR_NORMAL,
                "defaultActive": True if i == peak_idx else None,
            }
        )

    total = float(df["revenue"].sum())
    if gran == "month" and period_change_pct is not None:
        badge = f"{period_change_pct:+.1f}% vs previous month"
    elif len(series) >= 2 and series.iloc[-2] > 0:
        chg = 100 * (series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]
        badge = f"{chg:+.1f}% vs previous {gran}"
    else:
        badge = f"{len(series)} {gran}{'s' if len(series) != 1 else ''} tracked"
    return {"trendData": bars, "trendSummary": money(total), "trendBadge": badge, "granularity": gran}
