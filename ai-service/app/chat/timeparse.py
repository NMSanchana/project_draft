"""Natural-language time expressions -> :class:`TimeRange` (relative to the *data's* last date)."""

from __future__ import annotations

import re

import pandas as pd

from .plan import TimeRange

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1
    )
}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())} | {"sept": 9})
_MONTH_RX = re.compile(r"\b(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\b(?:\s*,?\s*(?:of\s+)?(20\d{2}))?", re.I)
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _year_for_month(month: int, dates: pd.Series) -> int:
    """The latest year in the data that contains this month (fallback: the last year)."""
    ym = dates.dt.to_period("M").unique()
    years = sorted({p.year for p in ym if p.month == month})
    return years[-1] if years else int(dates.max().year)


def months_in(text: str, dates: pd.Series) -> list[str]:
    """All ``YYYY-MM`` mentions in order of appearance."""
    out = []
    for m in _MONTH_RX.finditer(text):
        if m.group(1) == "may" and not m.group(2):  # lowercase "may" is almost always the verb
            continue
        month = MONTHS[m.group(1).lower()]
        year = int(m.group(2)) if m.group(2) else _year_for_month(month, dates)
        out.append(f"{year:04d}-{month:02d}")
    return out


def last_full_month(dates: pd.Series) -> str:
    from ..pipeline.kpis import last_full_months

    pair = last_full_months(dates)
    if pair:
        return str(pair[0])
    return str(dates.max().to_period("M"))


def parse_time(text: str, dates: pd.Series) -> TimeRange | None:
    t = text.lower()
    m = re.search(r"\b(?:last|past)\s+(\d{1,3}|" + "|".join(_NUM_WORDS) + r")\s+days?\b", t)
    if m:
        n = m.group(1)
        return TimeRange(last_days=int(n) if n.isdigit() else _NUM_WORDS[n])
    if re.search(r"\blast week\b", t):
        return TimeRange(last_days=7)
    if re.search(r"\blast month\b|\bprevious month\b", t):
        return TimeRange(month=last_full_month(dates))
    if re.search(r"\bthis month\b|\bcurrent month\b", t):
        return TimeRange(month=str(dates.max().to_period("M")))
    q = re.search(r"\bq([1-4])\b(?:\s*,?\s*(20\d{2}))?", t)
    if q:
        year = int(q.group(2)) if q.group(2) else int(dates.max().year)
        return TimeRange(quarter=f"{year}-Q{q.group(1)}")
    ms = months_in(text, dates)
    if ms:
        return TimeRange(month=ms[0])
    y = re.search(r"\b(?:in|during|for|of)\s+(20\d{2})\b|\b(20\d{2})\b", t)
    if y:
        return TimeRange(year=int(y.group(1) or y.group(2)))
    return None


def range_mask(dates: pd.Series, tr: TimeRange) -> pd.Series:
    """Boolean mask of rows inside ``tr`` (``last_days`` is relative to the data's last date)."""
    d = dates.dt.normalize()
    if tr.month:
        return d.dt.to_period("M") == pd.Period(tr.month)
    if tr.quarter:
        y, q = tr.quarter.split("-Q")
        return d.dt.to_period("Q") == pd.Period(f"{y}Q{q}")
    if tr.year:
        return d.dt.year == tr.year
    if tr.last_days:
        return d > d.max() - pd.Timedelta(days=tr.last_days)
    m = pd.Series(True, index=dates.index)
    if tr.start:
        m &= d >= pd.Timestamp(tr.start)
    if tr.end:
        m &= d <= pd.Timestamp(tr.end)
    return m


def describe(tr: TimeRange | None) -> str:
    if tr is None or tr.is_empty():
        return ""
    if tr.month:
        return pd.Period(tr.month).strftime("%B %Y")
    if tr.quarter:
        return tr.quarter.replace("-", " ")
    if tr.year:
        return str(tr.year)
    if tr.last_days:
        return f"the last {tr.last_days} days"
    return f"{tr.start or '...'} to {tr.end or '...'}"
