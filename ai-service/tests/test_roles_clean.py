import numpy as np
import pandas as pd
import pytest

from app.pipeline.assemble import run_fast_phase
from app.pipeline.clean import clean
from app.pipeline.ingest import DataError, read_csv_bytes, sanitize_filename
from app.pipeline.roles import detect_roles, to_numeric_series
from tests.conftest import SAMPLE_DIR


def _detect(path):
    return detect_roles(read_csv_bytes(path.read_bytes()).df)


def test_roles_sample_ecommerce():
    d = _detect(SAMPLE_DIR / "sample_ecommerce.csv").roles
    assert d == {
        "date": "order_date",
        "category": "category",
        "region": "region",
        "customer": "customer_id",
        "quantity": "quantity",
        "unit_price": "price",
        "cost": "cost",
        "revenue": "revenue",
    }


def test_roles_technova_different_names():
    d = _detect(SAMPLE_DIR / "technova_electronics_sales.csv").roles
    assert d == {
        "date": "order_date",
        "category": "product_category",
        "region": "region",
        "customer": "customer_id",
        "quantity": "units_sold",
        "unit_price": "unit_price",
        "cost": "cost",
        "revenue": "sales_amount",
    }


def _third_schema(n=300, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "Order No": [f"SO-{i // 2:05d}" for i in range(n)],
            "Sale Date": pd.date_range("2024-01-01", periods=n, freq="D").strftime("%d/%m/%Y"),
            "Client": [f"C{rng.integers(1, 40)}" for _ in range(n)],
            "Item Name": rng.choice([f"Widget {i}" for i in range(30)], n),
            "Department": rng.choice(["Tools", "Toys", "Home"], n),
            "Territory": rng.choice(["North", "South", "East"], n),
            "Qty": rng.integers(1, 6, n),
            "Unit Price": rng.uniform(5, 50, n).round(2),
            "Line Total": rng.uniform(10, 500, n).round(2),
            "Order Status": rng.choice(["shipped", "returned"], n),
        }
    )


def test_roles_third_schema_with_product_order_status():
    df = _third_schema()
    d = detect_roles(df.astype(str)).roles
    assert d["order_id"] == "Order No" and d["date"] == "Sale Date" and d["customer"] == "Client"
    assert d["product"] == "Item Name" and d["category"] == "Department" and d["region"] == "Territory"
    assert d["quantity"] == "Qty" and d["unit_price"] == "Unit Price" and d["revenue"] == "Line Total"
    assert d["status"] == "Order Status"


def test_value_based_fallbacks_when_headers_are_cryptic():
    df = pd.DataFrame({"a": pd.date_range("2024-01-01", periods=60).astype(str), "b": np.linspace(100, 900, 60), "c": ["x", "y"] * 30})
    det = detect_roles(df.astype(str))
    assert det.roles["date"] == "a" and det.roles["revenue"] == "b"
    assert det.confidence["revenue"] < 0.6 and det.notes


@pytest.mark.parametrize(
    "fname,qty,price", [("sample_ecommerce.csv", "quantity", "price"), ("technova_electronics_sales.csv", "units_sold", "unit_price")]
)
def test_golden_kpis_match_independent_pandas(fname, qty, price):
    raw = pd.read_csv(SAMPLE_DIR / fname)
    rev_col = "revenue" if "revenue" in raw else "sales_amount"
    fr = run_fast_phase((SAMPLE_DIR / fname).read_bytes(), fname, "ds1")
    a, k = fr.analytics, fr.kpis
    assert a["recordsCount"] == len(raw)
    assert a["revenue"] == pytest.approx(round(raw[rev_col].sum(), 2))
    # `cost` in these files is PER UNIT -> total cost = sum(cost * qty)
    assert fr.clean_result.report["cost_basis"] == "per_unit"
    exp_cost = (raw["cost"] * raw[qty]).sum()
    assert a["totalCost"] == pytest.approx(round(exp_cost, 2))
    assert a["totalProfit"] == pytest.approx(round(raw[rev_col].sum() - exp_cost, 2))
    assert a["profitMargin"] == pytest.approx(round(100 * (raw[rev_col].sum() - exp_cost) / raw[rev_col].sum(), 2))
    assert a["orders"] == len(raw)
    assert a["uniqueCustomers"] == raw["customer_id"].nunique()
    assert k["avg_order_value"] == pytest.approx(round(raw[rev_col].sum() / len(raw), 2))
    assert k["units"] == int(raw[qty].sum())


def test_period_change_uses_last_full_months():
    fr = run_fast_phase((SAMPLE_DIR / "technova_electronics_sales.csv").read_bytes(), "t.csv", "d")
    raw = pd.read_csv(SAMPLE_DIR / "technova_electronics_sales.csv", parse_dates=["order_date"])
    m = raw.groupby(raw.order_date.dt.to_period("M"))["sales_amount"].sum()
    pc = fr.kpis["period_change"]
    assert pc["basis"] == "month" and pc["current_label"] == "June 2024"  # July is partial -> skipped
    assert pc["change_pct"] == pytest.approx(round(100 * (m["2024-06"] - m["2024-05"]) / m["2024-05"], 2))


def test_trend_bars_match_frontend_format():
    fr = run_fast_phase((SAMPLE_DIR / "sample_ecommerce.csv").read_bytes(), "s.csv", "d")
    bars = fr.analytics["trendData"]
    assert [b["name"] for b in bars] == ["Jan", "Feb", "Mar"]
    assert all(b["heightPercent"].endswith("%") and b["value"].startswith("$") for b in bars)
    assert sum(1 for b in bars if b.get("defaultActive")) == 1
    assert max(b["numericValue"] for b in bars) == bars[[b.get("defaultActive", False) for b in bars].index(True)]["numericValue"]
    assert fr.analytics["trendSummary"] == f"${fr.analytics['revenue']:,.0f}"
    assert len({b["name"] for b in bars}) == len(bars)  # React key uniqueness


def test_cleaning_report_counts_and_quality_formula():
    df = pd.DataFrame(
        {
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-02", "not a date", "2024-01-05", "2024-01-06"],
            "revenue": ["100", "$1,200.50", "$1,200.50", "50", "-5", None],
            "customer_id": ["a", "b", "b", "c", "d", "e"],
        }
    )
    cr = clean(df, detect_roles(df))
    r = cr.report
    assert r["duplicates_removed"] == 1 and r["invalid_dates_removed"] == 1 and r["negative_rows_removed"] == 1
    assert r["imputed_values"]["revenue"] == 1 and r["rows_out"] == 3
    # the missing revenue is imputed with the median of the remaining values (100, 1200.5) -> 650.25
    assert cr.df["revenue"].tolist() == [100.0, 1200.5, 650.25]
    b = r["quality_breakdown"]
    assert r["quality_score"] == pytest.approx(sum(b.values()), abs=0.11) and 0 <= r["quality_score"] <= 100


def test_missing_optional_columns_never_crash():
    df = pd.DataFrame({"order_date": pd.date_range("2024-01-01", periods=40).astype(str), "revenue": range(40)})
    fr = run_fast_phase(df.to_csv(index=False).encode(), "min.csv", "d")
    a = fr.analytics
    assert a["totalCost"] == 0 and a["profitMargin"] == 0 and a["uniqueCustomers"] == 0
    assert any(i["id"] == "data-no-cost" for i in a["insights"])


@pytest.mark.parametrize(
    "payload,needle",
    [
        (b"", "empty"),
        (b"a,b\n", "no data rows"),
        (b"just one column\nx\ny\n", "Only one column"),
        (b"foo,bar\n1,2\n3,4\n", "No date column"),
        (b"order_date,note\n2024-01-01,hi\n2024-01-02,yo\n", "No revenue column"),
    ],
)
def test_unreadable_or_unsuitable_files_give_clear_errors(payload, needle):
    with pytest.raises(DataError, match=needle):
        run_fast_phase(payload, "x.csv", "d")


def test_encoding_and_delimiter_sniffing():
    txt = "order_date;revenue;région\n2024-01-01;10,5;Île\n2024-01-02;20;Île\n"
    res = read_csv_bytes(txt.encode("cp1252"))
    assert res.delimiter == ";" and "région" in res.df.columns
    bom = read_csv_bytes("\ufefforder_date,revenue\n2024-01-01,1\n".encode())
    assert list(bom.df.columns) == ["order_date", "revenue"]


def test_sanitize_filename_blocks_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd.csv"
    assert sanitize_filename("my sales (2024).CSV") == "my_sales_2024.csv"
    assert sanitize_filename(None) == "upload.csv"


def test_numeric_parsing_handles_currency_and_parentheses():
    s = to_numeric_series(pd.Series(["$1,234.50", "(20)", "€ 5", "abc", None]))
    assert s.iloc[:3].tolist() == [1234.5, -20.0, 5.0] and s.iloc[3:].isna().all()


def test_partial_months_are_labelled_in_tooltip_text():
    fr = run_fast_phase((SAMPLE_DIR / "technova_electronics_sales.csv").read_bytes(), "t.csv", "d")
    vals = {b["name"]: b["value"] for b in fr.analytics["trendData"]}
    assert vals["Jul"].endswith("(partial month)") and "partial" not in vals["Jun"]


def test_cancelled_and_returned_orders_are_excluded_from_revenue():
    df = pd.DataFrame(
        {
            "order_date": pd.date_range("2024-01-01", periods=10).astype(str),
            "revenue": [100.0] * 10,
            "status": [
                "Completed",
                "completed",
                "Cancelled",
                "returned",
                "Shipped",
                "refunded",
                "Delivered",
                "VOID",
                "failed",
                "completed",
            ],
        }
    )
    cr = clean(df, detect_roles(df))
    assert cr.report["status_excluded_rows"] == 5 and cr.report["rows_out"] == 5 and cr.df["revenue"].sum() == 500.0
    fr = run_fast_phase(df.to_csv(index=False).encode(), "s.csv", "d")
    assert fr.analytics["revenue"] == 500.0 and any("cancelled/returned" in i["desc"] for i in fr.analytics["insights"])
