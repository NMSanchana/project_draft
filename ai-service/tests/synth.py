"""Seeded synthetic sales data with planted patterns (shared by tests)."""

from __future__ import annotations

import numpy as np
import pandas as pd

CATS = {"Electronics": 300.0, "Home": 80.0, "Sports": 55.0, "Toys": 30.0}
REGIONS = ["North", "South", "East", "West"]


def make_sales(
    seed: int = 7, days: int = 180, start: str = "2024-01-01", spike_day: int | None = 100, dip_day: int | None = 140
) -> pd.DataFrame:
    """Canonical frame: weekly seasonality + mild trend + noise; planted spike (Electronics/West) and dip."""
    rng = np.random.default_rng(seed)
    rows, oid = [], 0
    dow_factor = np.array([1.0, 0.95, 0.9, 1.0, 1.15, 1.5, 1.35])
    for d in range(days):
        date = pd.Timestamp(start) + pd.Timedelta(days=d)
        n = rng.poisson(40 * dow_factor[date.dayofweek] * (1 + 0.003 * d))
        if dip_day is not None and d == dip_day:
            n = max(3, n // 6)
        for _ in range(n):
            cat = rng.choice(list(CATS), p=[0.25, 0.3, 0.25, 0.2])
            price = CATS[cat] * rng.uniform(0.9, 1.1)
            qty = int(rng.integers(1, 4))
            oid += 1
            rows.append((f"O{oid}", date, f"C{rng.integers(1, 300):03d}", cat, str(rng.choice(REGIONS)), qty, price))
        if spike_day is not None and d == spike_day:
            for _ in range(60):
                oid += 1
                rows.append((f"O{oid}", date, f"C{rng.integers(1, 300):03d}", "Electronics", "West", int(rng.integers(2, 5)), 300.0))
    df = pd.DataFrame(rows, columns=["order_id", "date", "customer", "category", "region", "quantity", "unit_price"])
    df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    df["cost"] = (df["revenue"] * 0.65).round(2)
    df["profit"] = df["revenue"] - df["cost"]
    return df


def spike_date(start: str = "2024-01-01", day: int = 100) -> str:
    return (pd.Timestamp(start) + pd.Timedelta(days=day)).strftime("%Y-%m-%d")
