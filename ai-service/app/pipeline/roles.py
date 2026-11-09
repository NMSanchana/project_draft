"""Column-role detection for arbitrary sales CSVs.

Each column is scored against each role using two signals:

* **name score** (75%): exact / head-noun / token / fuzzy match against a synonym table.
  The *head noun* rule makes ``product_category`` a category (not a product) and
  ``customer_id`` a customer (not an order id).
* **value score** (25%): does the data look like the role? (dates parse, quantities are
  small integers, regions have low cardinality, order ids are mostly unique ...). A failed
  value *gate* (e.g. a date column that does not parse) zeroes the score.

Roles are then assigned greedily by score, one column per role and one role per column.
The result carries a confidence per role so the UI / chat can be honest about guesses.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import pandas as pd

ROLES = [
    "date",
    "revenue",
    "cost",
    "profit",
    "quantity",
    "unit_price",
    "product",
    "category",
    "region",
    "customer",
    "order_id",
    "status",
]
NUMERIC_ROLES = {"revenue", "cost", "profit", "quantity", "unit_price"}
MIN_CONFIDENCE = 0.45
_HEAD_STOP = {"id", "no", "num", "number", "code", "key", "ref", "name", "sold", "at"}

# (synonym, weight). Multi-word synonyms use "_" as the joiner.
SYNONYMS: dict[str, list[tuple[str, float]]] = {
    "date": [
        ("date", 1),
        ("order_date", 1),
        ("purchase_date", 1),
        ("invoice_date", 1),
        ("transaction_date", 1),
        ("sale_date", 1),
        ("datetime", 1),
        ("timestamp", 0.9),
        ("created_at", 0.9),
        ("created", 0.8),
        ("ordered", 0.6),
        ("time", 0.6),
        ("day", 0.5),
        ("period", 0.4),
    ],
    "revenue": [
        ("revenue", 1),
        ("sales_amount", 1),
        ("sales", 0.9),
        ("line_total", 1),
        ("total_sales", 1),
        ("net_sales", 1),
        ("gross_sales", 1),
        ("order_total", 1),
        ("total_amount", 1),
        ("sale_amount", 1),
        ("amount", 0.8),
        ("turnover", 0.9),
        ("gmv", 0.9),
        ("income", 0.7),
        ("total", 0.6),
        ("value", 0.4),
    ],
    "cost": [
        ("cost", 1),
        ("unit_cost", 1),
        ("total_cost", 1),
        ("cogs", 1),
        ("cost_of_goods", 1),
        ("purchase_cost", 0.9),
        ("cost_price", 0.9),
        ("expense", 0.8),
        ("expenses", 0.8),
    ],
    "profit": [("profit", 1), ("net_profit", 1), ("gross_profit", 1), ("margin_amount", 1), ("earnings", 0.6)],
    "quantity": [
        ("quantity", 1),
        ("qty", 1),
        ("units_sold", 1),
        ("unit_sold", 1),
        ("order_quantity", 1),
        ("units", 0.95),
        ("pieces", 0.8),
        ("num_items", 0.8),
        ("volume", 0.6),
        ("count", 0.5),
        ("items", 0.5),
    ],
    "unit_price": [
        ("unit_price", 1),
        ("selling_price", 1),
        ("sale_price", 1),
        ("price_per_unit", 1),
        ("price", 0.95),
        ("list_price", 0.9),
        ("mrp", 0.8),
        ("rate", 0.5),
    ],
    "product": [
        ("product", 1),
        ("product_name", 1),
        ("item_name", 1),
        ("item", 0.8),
        ("sku", 0.9),
        ("product_id", 0.9),
        ("goods", 0.6),
        ("title", 0.4),
        ("description", 0.4),
        ("model", 0.4),
    ],
    "category": [
        ("category", 1),
        ("product_category", 1),
        ("sub_category", 0.8),
        ("product_type", 0.9),
        ("department", 0.8),
        ("segment", 0.6),
        ("type", 0.5),
        ("class", 0.5),
        ("group", 0.5),
        ("genre", 0.5),
    ],
    "region": [
        ("region", 1),
        ("territory", 0.9),
        ("state", 0.8),
        ("city", 0.8),
        ("country", 0.8),
        ("location", 0.8),
        ("zone", 0.8),
        ("area", 0.7),
        ("province", 0.7),
        ("store", 0.6),
        ("branch", 0.6),
        ("market", 0.6),
    ],
    "customer": [
        ("customer", 1),
        ("customer_id", 1),
        ("client_id", 1),
        ("cust_id", 1),
        ("client", 0.9),
        ("customer_name", 0.9),
        ("customer_key", 0.9),
        ("buyer", 0.9),
        ("user_id", 0.8),
        ("account", 0.5),
        ("user", 0.5),
    ],
    "order_id": [
        ("order_id", 1),
        ("order_no", 1),
        ("order_number", 1),
        ("invoice_no", 1),
        ("invoice_id", 1),
        ("transaction_id", 1),
        ("txn_id", 1),
        ("basket_id", 1),
        ("order_ref", 1),
        ("invoice", 0.9),
        ("receipt", 0.8),
        ("transaction", 0.6),
        ("order", 0.6),
    ],
    "status": [("status", 1), ("order_status", 1), ("payment_status", 0.9)],
}


@dataclass
class RoleDetection:
    """Result of role detection."""

    roles: dict[str, str] = field(default_factory=dict)  # role -> source column name
    confidence: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    derived: dict[str, str] = field(default_factory=dict)  # role -> how it will be derived

    def get(self, role: str) -> str | None:
        return self.roles.get(role)


# --------------------------------------------------------------------------- helpers
def tokenize(name: str) -> list[str]:
    """``'Product Category'``/``'productCategory'``/``'product-category'`` -> ``['product','category']``."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(name))
    return [t for t in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if t]


def to_numeric_series(s: pd.Series) -> pd.Series:
    """Parse numbers that may contain currency symbols, thousands separators or (negatives)."""
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return pd.to_numeric(s, errors="coerce").astype("float64")
    txt = s.astype("string").str.strip()
    txt = txt.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    txt = txt.str.replace(r"[,\s$€£₹¥]", "", regex=True)
    return pd.to_numeric(txt, errors="coerce").astype("float64")  # plain NaN, never pd.NA


def parse_dates(s: pd.Series) -> pd.Series:
    """Fast uniform-format parse first, then a slower per-element pass for leftovers."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = pd.to_datetime(s, errors="coerce", utc=True)
        miss = out.isna() & s.notna()
        if miss.any() and miss.sum() < len(s):
            out.loc[miss] = pd.to_datetime(s[miss], errors="coerce", format="mixed", utc=True)
    return out.dt.tz_localize(None)


def _name_score(role: str, toks: list[str]) -> float:
    if not toks:
        return 0.0
    joined = "_".join(toks)
    stripped = [t for t in toks if t not in _HEAD_STOP] or toks
    head = stripped[-1]
    best = 0.0
    for syn, weight in SYNONYMS[role]:
        st = syn.split("_")
        if joined == syn:
            s = 1.0
        elif len(st) == 1:
            if head == syn:
                s = 0.9
            elif syn in toks:
                s = 0.65
            elif max(SequenceMatcher(None, t, syn).ratio() for t in toks) >= 0.86 and len(syn) > 3:
                s = 0.5
            else:
                s = 0.0
        else:
            n = len(st)
            if any(toks[i : i + n] == st for i in range(len(toks) - n + 1)):
                s = 0.9
            elif all(t in toks for t in st):
                s = 0.7
            else:
                s = 0.0
        best = max(best, s * weight)
    return best


@dataclass
class _Profile:
    n: int
    nunique: int
    unique_ratio: float
    numeric_rate: float
    date_rate: float
    int_like: float
    positive: float
    median: float


def _profile(s: pd.Series) -> _Profile:
    nn = s.dropna()
    if len(nn) == 0:
        return _Profile(0, 0, 0, 0, 0, 0, 0, 0)
    step = max(1, len(nn) // 5000)
    sample = nn.iloc[::step]
    num = to_numeric_series(sample)
    numeric_rate = float(num.notna().mean())
    date_rate = 0.0
    if numeric_rate < 0.95 or sample.astype(str).str.len().eq(8).all():
        date_rate = float(parse_dates(sample.astype(str)).notna().mean())
    vals = num.dropna()
    return _Profile(
        n=len(nn),
        nunique=int(nn.nunique()),
        unique_ratio=float(nn.nunique() / len(nn)),
        numeric_rate=numeric_rate,
        date_rate=date_rate,
        int_like=float((vals == vals.round()).mean()) if len(vals) else 0.0,
        positive=float((vals > 0).mean()) if len(vals) else 0.0,
        median=float(vals.median()) if len(vals) else 0.0,
    )


def _value_score(role: str, p: _Profile) -> float:
    """Return 0 when the data cannot plausibly play the role (gate), else a 0..1 fit score."""
    if p.n == 0:
        return 0.0
    if role == "date":
        return p.date_rate if p.date_rate >= 0.8 else 0.0
    if role in NUMERIC_ROLES:
        if p.numeric_rate < 0.9:
            return 0.0
        if role == "quantity":
            return 0.6 * p.int_like + 0.4 * float(p.median < 1000)
        if role == "profit":
            return 1.0
        return 1.0 if p.positive >= 0.9 else 0.5
    if role == "category":
        return 1.0 if (p.nunique <= 100 and p.unique_ratio <= 0.5) else 0.0
    if role == "region":
        return 1.0 if (p.nunique <= 300 and p.unique_ratio <= 0.5) else 0.0
    if role == "product":
        return 1.0 if p.unique_ratio <= 0.9 and p.nunique >= 2 else 0.0
    if role == "customer":
        return 1.0 if p.nunique >= 2 else 0.0
    if role == "order_id":
        return p.unique_ratio if p.unique_ratio >= 0.3 else 0.0
    if role == "status":
        return 1.0 if p.nunique <= 12 and p.numeric_rate < 0.9 else 0.0
    return 0.0


# --------------------------------------------------------------------------- main API
def detect_roles(df: pd.DataFrame) -> RoleDetection:
    """Detect the business role of each column. Never raises on odd data."""
    det = RoleDetection()
    profiles = {c: _profile(df[c]) for c in df.columns}
    toks = {c: tokenize(c) for c in df.columns}

    candidates: list[tuple[float, int, str, str]] = []
    for ci, col in enumerate(df.columns):
        for role in ROLES:
            ns = _name_score(role, toks[col])
            if ns <= 0:
                continue
            vs = _value_score(role, profiles[col])
            if vs <= 0:
                continue
            candidates.append((0.75 * ns + 0.25 * vs, -ci, col, role))
    candidates.sort(reverse=True)

    used_cols: set[str] = set()
    for score, _, col, role in candidates:
        if score < MIN_CONFIDENCE or role in det.roles or col in used_cols:
            continue
        det.roles[role] = col
        det.confidence[role] = round(float(score), 3)
        used_cols.add(col)

    # ---- value-only fallbacks -------------------------------------------------
    if "date" not in det.roles:
        best = max(
            ((profiles[c].date_rate, c) for c in df.columns if c not in used_cols and profiles[c].date_rate >= 0.8),
            default=None,
        )
        if best:
            det.roles["date"], det.confidence["date"] = best[1], round(best[0] * 0.6, 3)
            used_cols.add(best[1])
            det.notes.append(f"Date column '{best[1]}' was inferred from its values (no matching header).")

    if "revenue" not in det.roles:
        if "quantity" in det.roles and "unit_price" in det.roles:
            det.derived["revenue"] = "quantity * unit_price"
            det.notes.append("No revenue column found; revenue is derived as quantity x unit price.")
        else:
            id_like = lambda c: "id" in toks[c]  # noqa: E731
            numeric = [
                (float(to_numeric_series(df[c]).clip(lower=0).sum()), c)
                for c in df.columns
                if c not in used_cols and profiles[c].numeric_rate >= 0.9 and not id_like(c) and profiles[c].positive >= 0.9
            ]
            if numeric:
                _, col = max(numeric)
                det.roles["revenue"], det.confidence["revenue"] = col, 0.3
                used_cols.add(col)
                det.notes.append(f"Revenue was guessed from the values of column '{col}' (low confidence); please verify.")

    for role, conf in list(det.confidence.items()):
        if conf < 0.6:
            det.notes.append(f"Low confidence ({conf:.2f}) mapping {role} -> '{det.roles[role]}'.")
    return det
