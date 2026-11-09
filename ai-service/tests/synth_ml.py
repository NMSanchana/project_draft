"""Seeded synthetic datasets with planted patterns for the ML-module tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

START = pd.Timestamp("2024-01-01")


def make_customers(seed: int = 3, days: int = 240) -> pd.DataFrame:
    """Loyal (every ~7d), regular (~18d), and a group that STOPS buying 25 days before the end (+ one-offs)."""
    rng = np.random.default_rng(seed)
    rows, oid = [], 0
    groups = [("L", 120, 7, days, 100), ("R", 120, 18, days, 60), ("S", 100, 8, days - 25, 80)]
    for tag, n, gap, stop, spend in groups:
        for i in range(n):
            t = float(rng.uniform(0, gap))
            while t < stop:
                oid += 1
                rows.append((f"{tag}{i:03d}", START + pd.Timedelta(days=int(t)), f"O{oid}", float(rng.uniform(0.7, 1.3) * spend)))
                t += max(1.0, rng.normal(gap, gap * 0.15))
    for i in range(60):
        oid += 1
        rows.append((f"X{i:03d}", START + pd.Timedelta(days=int(rng.integers(0, days))), f"O{oid}", float(rng.uniform(20, 60))))
    return pd.DataFrame(rows, columns=["customer", "date", "order_id", "revenue"])


def make_drivers(seed: int = 5) -> pd.DataFrame:
    """Jan vs Feb 2024. A-West halves in Feb (the planted driver); category B gets a +10% price rise."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in pd.date_range("2024-01-01", "2024-02-29"):
        feb = d.month == 2
        for cat, base in (("A", 100.0), ("B", 50.0)):
            for reg in ("East", "West"):
                n = 6
                if cat == "A" and reg == "West" and feb:
                    n = 3
                price = base * (1.10 if (cat == "B" and feb) else 1.0)
                for _ in range(n):
                    q = int(rng.integers(1, 4))
                    rows.append((d, cat, reg, q, price, q * price))
    return pd.DataFrame(rows, columns=["date", "category", "region", "quantity", "unit_price", "revenue"])


def make_pricing(seed: int = 11, n_per: int = 1500) -> pd.DataFrame:
    """Planted elasticities: Inelastic -0.5, Elastic -2.0, Fixed (constant price). Cost = 60% of base price."""
    rng = np.random.default_rng(seed)
    rows = []
    for cat, e, base, sd in (("Inelastic", -0.5, 40.0, 0.2), ("Elastic", -2.0, 25.0, 0.2), ("Fixed", -1.0, 15.0, 0.0)):
        for i in range(n_per):
            price = base * float(np.exp(rng.normal(0, sd))) if sd else base
            q = max(1, int(rng.poisson(10 * (price / base) ** e)))
            d = START + pd.Timedelta(days=int(rng.integers(0, 90)))
            rows.append(
                (
                    f"O{len(rows)}",
                    d,
                    f"C{rng.integers(1, 200)}",
                    cat,
                    str(rng.choice(["N", "S"])),
                    q,
                    round(price, 2),
                    round(q * price, 2),
                    round(q * base * 0.6, 2),
                )
            )
    return pd.DataFrame(rows, columns=["order_id", "date", "customer", "category", "region", "quantity", "unit_price", "revenue", "cost"])


def make_baskets(seed: int = 9, n_orders: int = 800) -> pd.DataFrame:
    """Planted pairs: Monitor+HDMI Cable (~45%) and Laptop+Mouse (~55%); other items independent."""
    rng = np.random.default_rng(seed)
    items = ["Monitor", "HDMI Cable", "Laptop", "Mouse", "Keyboard", "Desk", "Chair", "Webcam"]
    rows = []
    for o in range(n_orders):
        basket = {str(rng.choice(items))}
        if "Monitor" in basket and rng.random() < 0.9:
            basket.add("HDMI Cable")
        if "Laptop" in basket and rng.random() < 0.9:
            basket.add("Mouse")
        if rng.random() < 0.3:
            basket.add(str(rng.choice(items)))
        d = START + pd.Timedelta(days=int(rng.integers(0, 90)))
        for it in basket:
            rows.append((f"O{o}", d, f"C{rng.integers(1, 300)}", it, float(rng.uniform(10, 200))))
    return pd.DataFrame(rows, columns=["order_id", "date", "customer", "product", "revenue"])
