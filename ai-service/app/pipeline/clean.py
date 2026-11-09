"""Cleaning: build a canonical, typed DataFrame from the raw string frame + a cleaning report.

Canonical columns (present only when the role was detected/derivable):
``date, revenue, cost, profit, quantity, unit_price, product, category, region, customer, order_id, status``

Rows whose ``status`` is cancelled / void / failed / refunded / returned are excluded (counted in the report).

``cost`` in the canonical frame is always the **line total** cost. Many CSVs store a per-unit
cost; this is detected from the data (see :func:`_infer_cost_basis`) and converted.

Quality score (0-100) = completeness (40) + uniqueness (15) + validity (25) + coverage (20):

* completeness = 40 * (1 - missing cells / cells, over the detected role columns)
* uniqueness   = 15 * (1 - min(1, 5 * duplicate_rows / rows))
* validity     = 25 * (1 - min(1, 5 * invalid / rows)), invalid = unparseable dates + negative rows
                 + unparseable numbers
* coverage     = 20 * found / 7 of: date, revenue, cost-or-profit, quantity, product-or-category,
                 region, customer
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .ingest import DataError
from .roles import NUMERIC_ROLES, RoleDetection, parse_dates, to_numeric_series

TEXT_ROLES = ["product", "category", "region", "customer", "order_id", "status"]


@dataclass
class CleanResult:
    df: pd.DataFrame
    report: dict
    roles: RoleDetection


def _infer_cost_basis(cost: pd.Series, qty: pd.Series | None, unit_price: pd.Series | None, revenue: pd.Series, header: str) -> str:
    """Return ``'per_unit'`` or ``'line_total'``.

    A per-unit cost never exceeds the unit price. A line-total cost on multi-unit rows usually
    does. So on rows with quantity > 1 we check how often ``cost <= unit_price``.
    """
    if qty is None:
        return "line_total"
    if "unit" in header.lower().replace("_", " ").split():
        return "per_unit"
    price = unit_price if unit_price is not None else revenue / qty.replace(0, np.nan)
    multi = (qty > 1) & price.notna() & cost.notna()
    if multi.sum() < 20:
        return "line_total"
    share = float((cost[multi] <= price[multi] * 1.0001).mean())
    return "per_unit" if share >= 0.9 else "line_total"


def clean(raw: pd.DataFrame, det: RoleDetection) -> CleanResult:
    """Clean ``raw`` using detected roles. Raises :class:`DataError` for unusable data."""
    roles = det.roles
    if "date" not in roles:
        raise DataError(
            "No date column found. Add a column such as 'order_date' (e.g. 2024-03-15). "
            f"Columns seen: {', '.join(map(str, raw.columns[:15]))}."
        )
    if "revenue" not in roles and "revenue" not in det.derived:
        raise DataError(
            "No revenue column found. Add a column such as 'revenue' or 'sales_amount' "
            "(or both 'quantity' and 'price'). "
            f"Columns seen: {', '.join(map(str, raw.columns[:15]))}."
        )

    report: dict = {"rows_in": int(len(raw))}
    df = raw.dropna(how="all")
    report["empty_rows_removed"] = int(len(raw) - len(df))
    n_dup = int(df.duplicated().sum())
    df = df.drop_duplicates()
    report["duplicates_removed"] = n_dup
    # orders that never produced revenue (cancelled / voided / failed / refunded / returned) are excluded
    excluded = 0
    if "status" in roles:
        st = df[roles["status"]].astype("string").str.lower()
        bad = st.str.contains(r"cancel|void|fail|refund|^return", regex=True, na=False).astype(bool)
        excluded = int(bad.sum())
        df = df[~bad]
    report["status_excluded_rows"] = excluded
    rows_after_dedupe = len(df)

    role_cols = list(dict.fromkeys(roles.values()))
    cells = max(1, len(df) * max(1, len(role_cols)))
    missing_cells = int(df[role_cols].isna().sum().sum())
    report["missing_before_pct"] = round(100 * missing_cells / cells, 2)

    out = pd.DataFrame(index=df.index)
    out["date"] = parse_dates(df[roles["date"]])
    unparsed_numbers = 0
    for role in NUMERIC_ROLES:
        if role in roles:
            col = df[roles[role]]
            parsed = to_numeric_series(col)
            unparsed_numbers += int((parsed.isna() & col.notna()).sum())
            out[role] = parsed
    for role in TEXT_ROLES:
        if role in roles:
            out[role] = df[roles[role]]

    notes = list(det.notes)

    # ---- derive missing numeric roles ------------------------------------------------
    if "revenue" not in out and "revenue" in det.derived:
        out["revenue"] = out["quantity"] * out["unit_price"]
    if "unit_price" not in out and "quantity" in out:
        out["unit_price"] = out["revenue"] / out["quantity"].replace(0, np.nan)
        report["unit_price_derived"] = True

    # ---- invalid rows ---------------------------------------------------------------
    keep = out["date"].notna()
    report["invalid_dates_removed"] = int((~keep).sum())
    neg = pd.Series(False, index=out.index)
    for role in ("revenue", "quantity", "cost", "unit_price"):
        if role in out:
            neg |= out[role] < 0
    report["negative_rows_removed"] = int((neg & keep).sum())
    out = out[keep & ~neg]

    if out.empty:
        raise DataError("No valid rows remain after cleaning (dates unparseable or values negative).")

    # ---- imputation -----------------------------------------------------------------
    imputed: dict[str, int] = {}
    for role in NUMERIC_ROLES:
        if role in out and out[role].isna().any():
            n = int(out[role].isna().sum())
            if role == "revenue" and "quantity" in out and "unit_price" in out:
                fill = out["quantity"] * out["unit_price"]
                out["revenue"] = out["revenue"].fillna(fill)
            med = out[role].median()
            out[role] = out[role].fillna(0.0 if pd.isna(med) else med)
            imputed[role] = n
    for role in ("product", "category", "region", "status"):
        if role in out and out[role].isna().any():
            n = int(out[role].isna().sum())
            mode = out[role].mode()
            out[role] = out[role].fillna(mode.iloc[0] if len(mode) else "Unknown")
            imputed[role] = n
    if "customer" in out and out["customer"].isna().any():
        imputed["customer"] = int(out["customer"].isna().sum())
        out["customer"] = out["customer"].fillna("Unknown")
    if "order_id" in out and out["order_id"].isna().any():
        mask = out["order_id"].isna()
        imputed["order_id"] = int(mask.sum())
        out.loc[mask, "order_id"] = "ROW" + out.index[mask].astype(str)
    report["imputed_values"] = imputed
    report["unparseable_numeric_values"] = unparsed_numbers

    # ---- cost / profit ----------------------------------------------------------------
    qty = out["quantity"] if "quantity" in out else None
    unit_price = out["unit_price"] if "unit_price" in out else None
    cost_basis = None
    if "cost" in out:
        cost_basis = _infer_cost_basis(out["cost"], qty, unit_price, out["revenue"], roles.get("cost", ""))
        if cost_basis == "per_unit" and qty is not None:
            out["cost"] = out["cost"] * qty
            notes.append(f"Column '{roles['cost']}' is a per-unit cost; multiplied by quantity to get line cost.")
    report["cost_basis"] = cost_basis

    profit_check = None
    if "cost" in out:
        calc = out["revenue"] - out["cost"]
        if "profit" in out:
            denom = max(1.0, float(out["revenue"].abs().sum()))
            profit_check = {
                "max_abs_diff": round(float((calc - out["profit"]).abs().max()), 2),
                "relative_diff_pct": round(100 * float((calc - out["profit"]).abs().sum()) / denom, 3),
            }
        out["profit"] = calc
    elif "profit" in out:
        out["cost"] = out["revenue"] - out["profit"]
    report["profit_check"] = profit_check

    out = out.sort_values("date", kind="stable").reset_index(drop=True)

    # ---- quality score ----------------------------------------------------------------
    rows_in = max(1, rows_after_dedupe)
    invalid = report["invalid_dates_removed"] + report["negative_rows_removed"] + unparsed_numbers
    found = sum(
        [
            True,  # date (required)
            True,  # revenue (required)
            "cost" in roles or "profit" in roles,
            "quantity" in roles,
            "product" in roles or "category" in roles,
            "region" in roles,
            "customer" in roles,
        ]
    )
    breakdown = {
        "completeness": round(40 * (1 - missing_cells / cells), 1),
        "uniqueness": round(15 * (1 - min(1.0, 5 * n_dup / max(1, report["rows_in"]))), 1),
        "validity": round(25 * (1 - min(1.0, 5 * invalid / rows_in)), 1),
        "coverage": round(20 * found / 7, 1),
    }
    report["quality_breakdown"] = breakdown
    report["quality_score"] = round(sum(breakdown.values()), 1)
    report["rows_out"] = int(len(out))
    report["date_range"] = [out["date"].min().strftime("%Y-%m-%d"), out["date"].max().strftime("%Y-%m-%d")]
    report["notes"] = notes
    report["detected_roles"] = {r: {"column": c, "confidence": det.confidence.get(r)} for r, c in roles.items()}
    report["derived_roles"] = dict(det.derived)
    report["missing_roles"] = [r for r in ("cost", "quantity", "product", "category", "region", "customer", "order_id") if r not in out]
    return CleanResult(df=out, report=report, roles=det)
