#!/usr/bin/env python3
"""Generate ``sample-data/retail_with_orders.csv`` (seeded, reproducible) plus the sample PDFs.

Columns: order_id, date, customer_id, product, category, region, quantity, unit_price, cost, revenue, status
(``cost`` is per unit, like the two original sample files). One year of data (2023-07-01 to 2024-06-30).

Planted patterns, so every module has something real to find:
  * seasonality ........ weekly cycle (weekend peak) + a yearly wave peaking in December + mild growth
  * anomalies .......... 2024-02-14 flash-sale SPIKE (Electronics in the West)  and  2024-03-09 outage DIP
  * revenue drivers .... from 2024-06-01 the South region loses ~65% of its orders (June vs May)
  * price elasticity ... Groceries elastic (-1.8), Furniture inelastic (-0.5), Electronics (-1.1);
                         Office has constant prices (the system must say "insufficient evidence")
  * cross-sell ......... Monitor -> HDMI Cable, Laptop -> Mouse, Desk -> Chair, Coffee -> Snacks
  * churn .............. ~8% of (frequent) customers stop buying on 2024-06-10 (still "active", about to lapse);
                         ~10% stopped on 2024-04-30 (already lapsed)
  * low margin ......... Groceries cost is 88% of price (12% margin, below the 15% rule)
  * status ............. ~4% returned and ~2% cancelled orders (excluded by the cleaning step)

Usage:  python scripts/generate_sample_data.py [--seed 42]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample-data" / "retail_with_orders.csv"

START, END = pd.Timestamp("2023-07-01"), pd.Timestamp("2024-06-30")
SPIKE_DAY, DIP_DAY = pd.Timestamp("2024-02-14"), pd.Timestamp("2024-03-09")
SOUTH_DROP_FROM = pd.Timestamp("2024-06-01")
LAPSED_STOP, STOPPING_STOP = pd.Timestamp("2024-04-30"), pd.Timestamp("2024-06-03")

# product -> (category, base price, cost ratio, typical units per line)
PRODUCTS = {
    "Laptop": ("Electronics", 900.0, 0.78, 1.3),
    "Monitor": ("Electronics", 250.0, 0.74, 1.6),
    "HDMI Cable": ("Electronics", 15.0, 0.55, 3.0),
    "Keyboard": ("Electronics", 60.0, 0.65, 2.5),
    "Mouse": ("Electronics", 25.0, 0.60, 3.0),
    "Desk": ("Furniture", 300.0, 0.62, 1.5),
    "Chair": ("Furniture", 150.0, 0.60, 2.5),
    "Lamp": ("Furniture", 40.0, 0.55, 3.0),
    "Coffee": ("Groceries", 12.0, 0.88, 6.0),
    "Tea": ("Groceries", 8.0, 0.88, 6.0),
    "Snacks": ("Groceries", 5.0, 0.88, 8.0),
    "Notebook": ("Office", 6.0, 0.50, 6.0),
    "Pens": ("Office", 4.0, 0.45, 8.0),
}
ELASTICITY = {"Electronics": -1.1, "Furniture": -0.5, "Groceries": -1.8, "Office": -1.0}
PRICE_NOISE = {"Electronics": 0.10, "Furniture": 0.12, "Groceries": 0.15, "Office": 0.0}  # Office: constant prices
CATEGORY_P = {"Electronics": 0.27, "Furniture": 0.18, "Groceries": 0.35, "Office": 0.20}
COMPANION = {"Monitor": ("HDMI Cable", 0.70), "Laptop": ("Mouse", 0.55), "Desk": ("Chair", 0.50), "Coffee": ("Snacks", 0.45)}
REGIONS = ["North", "South", "East", "West"]
DOW = np.array([0.95, 0.90, 0.90, 1.00, 1.15, 1.45, 1.30])  # Mon..Sun


def _line(rng, product: str, price_mult: float = 1.0, qty_boost: tuple[int, int] | None = None) -> tuple[int, float, float]:
    cat, base, cost_ratio, lam = PRODUCTS[product]
    sd = PRICE_NOISE[cat]
    price = round(base * (float(np.exp(rng.normal(0, sd))) if sd else 1.0) * price_mult, 2)
    if qty_boost:
        qty = int(rng.integers(*qty_boost))
    else:
        qty = max(1, int(rng.poisson(lam * (price / base) ** ELASTICITY[cat])))
    return qty, price, round(base * cost_ratio, 2)


def generate(seed: int = 42) -> pd.DataFrame:
    """Return the dataset. ``df.attrs`` lists the planted customer groups for tests."""
    rng = np.random.default_rng(seed)
    n_cust = 600
    cust = np.array([f"CU{i:04d}" for i in range(1, n_cust + 1)])
    group = rng.choice(["regular", "lapsed", "stopping"], size=n_cust, p=[0.82, 0.10, 0.08])
    stop = np.where(
        group == "lapsed",
        np.datetime64(LAPSED_STOP),
        np.where(group == "stopping", np.datetime64(STOPPING_STOP), np.datetime64("2100-01-01")),
    )
    weight = rng.lognormal(0, 0.6, n_cust)
    weight = np.where(group == "stopping", weight * 3.0, weight)  # the at-risk group were frequent buyers
    cats = list(CATEGORY_P)
    by_cat = {c: [p for p, v in PRODUCTS.items() if v[0] == c] for c in cats}

    rows, oid = [], 0

    def add_order(date, customer, region, lines, status):
        nonlocal oid
        oid += 1
        for product, qty, price, cost in lines:
            cat = PRODUCTS[product][0]
            rows.append(
                (
                    f"SO-{oid:06d}",
                    date.strftime("%Y-%m-%d"),
                    customer,
                    product,
                    cat,
                    region,
                    qty,
                    price,
                    cost,
                    round(qty * price, 2),
                    status,
                )
            )

    for date in pd.date_range(START, END):
        t = (date - START).days
        season = 1 + 0.25 * np.sin(2 * np.pi * (date.dayofyear - 330) / 365)
        south_lost = date >= SOUTH_DROP_FROM  # South loses ~65% of its orders (they are LOST, not moved)
        n = rng.poisson(44 * DOW[date.dayofweek] * season * (1 + 0.0008 * t) * (0.84 if south_lost else 1.0))
        if date == DIP_DAY:
            n = int(n * 0.12)
        active = (stop >= np.datetime64(date)).astype(float)
        p = weight * active
        p /= p.sum()
        customers = rng.choice(n_cust, size=n, p=p)
        rw = np.array([0.25, 0.25 * (0.35 if south_lost else 1.0), 0.25, 0.25])
        rw = rw / rw.sum()
        for ci in customers:
            region = REGIONS[int(rng.choice(4, p=rw))]
            cat = cats[int(rng.choice(len(cats), p=list(CATEGORY_P.values())))]
            product = str(rng.choice(by_cat[cat]))
            lines = [(product, *_line(rng, product))]
            comp = COMPANION.get(product)
            if comp and rng.random() < comp[1]:
                lines.append((comp[0], *_line(rng, comp[0])))
            if rng.random() < 0.08:
                extra = str(rng.choice(list(PRODUCTS)))
                if extra not in {x[0] for x in lines}:
                    lines.append((extra, *_line(rng, extra)))
            r = rng.random()
            add_order(date, cust[ci], region, lines, "returned" if r < 0.04 else ("cancelled" if r < 0.06 else "completed"))
        if date == SPIKE_DAY:  # flash sale: many large Electronics orders in the West
            for _ in range(140):
                product = str(rng.choice(["Laptop", "Monitor", "Keyboard"]))
                add_order(date, cust[int(rng.choice(n_cust, p=p))], "West", [(product, *_line(rng, product, 0.9, (2, 5)))], "completed")

    df = pd.DataFrame(
        rows,
        columns=["order_id", "date", "customer_id", "product", "category", "region", "quantity", "unit_price", "cost", "revenue", "status"],
    )
    df.attrs["stopping_customers"] = sorted(cust[group == "stopping"].tolist())
    df.attrs["lapsed_customers"] = sorted(cust[group == "lapsed"].tolist())
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    df = generate(args.seed)
    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)
    ok = df[df["status"] == "completed"]
    print(
        f"wrote {OUT.relative_to(ROOT)}: {len(df):,} rows ({len(ok):,} completed), {df['order_id'].nunique():,} orders, "
        f"{df['customer_id'].nunique()} customers, revenue (completed) ${ok['revenue'].sum():,.0f}"
    )
    try:
        import generate_sample_docs

        generate_sample_docs.main()
    except Exception as exc:  # noqa: BLE001 - reportlab missing etc.
        print("sample PDFs not generated:", exc)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
