import time

import numpy as np
import pandas as pd

from app.pipeline.assemble import run_fast_phase
from tests.conftest import SAMPLE_DIR, auth

SAMPLE = SAMPLE_DIR / "sample_ecommerce.csv"
UPLOAD = lambda p=SAMPLE, name=None: {"file": (name or p.name, p.read_bytes(), "text/csv")}  # noqa: E731
ALICE = dict(user_id="alice-id", email="alice@x.com")
BOB = dict(user_id="bob-id", email="bob@x.com")


def test_analyze_returns_full_processed_analytics_then_becomes_ready(client):
    r = client.post("/ai/v1/datasets/analyze", files=UPLOAD(), headers=auth(**ALICE))
    assert r.status_code == 200, r.text
    a = r.json()
    for key in (
        "fileName",
        "recordsCount",
        "revenue",
        "totalCost",
        "totalProfit",
        "profitMargin",
        "orders",
        "uniqueCustomers",
        "trendData",
        "trendSummary",
        "trendBadge",
        "insights",
        "activities",
    ):
        assert key in a
    assert a["status"] == "enriching" and a["datasetId"] and a["quality"]["detected_roles"]["revenue"]["column"] == "revenue"
    assert a["activities"][0]["status"] == "Completed" and a["activities"][0]["accuracy"].endswith("%")
    # TestClient runs background tasks before returning -> polling shows 'ready'
    g = client.get(f"/ai/v1/datasets/{a['datasetId']}", headers=auth(**ALICE)).json()
    assert g["status"] == "ready" and g["revenue"] == a["revenue"]


def test_list_and_isolation_between_users(client):
    ds = client.post("/ai/v1/datasets/analyze", files=UPLOAD(), headers=auth(**ALICE)).json()["datasetId"]
    assert ds in [d["datasetId"] for d in client.get("/ai/v1/datasets", headers=auth(**ALICE)).json()]
    assert client.get("/ai/v1/datasets", headers=auth(**BOB)).json() == []
    r = client.get(f"/ai/v1/datasets/{ds}", headers=auth(**BOB))
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"
    assert client.delete(f"/ai/v1/datasets/{ds}", headers=auth(**BOB)).status_code == 403
    assert client.get("/ai/v1/datasets/doesnotexist", headers=auth(**ALICE)).status_code == 404


def test_delete_removes_everything(client):
    ds = client.post("/ai/v1/datasets/analyze", files=UPLOAD(), headers=auth(**ALICE)).json()["datasetId"]
    from app.storage import dataset_dir

    assert dataset_dir("alice-id", ds).exists()
    assert client.delete(f"/ai/v1/datasets/{ds}", headers=auth(**ALICE)).status_code == 200
    assert not dataset_dir("alice-id", ds).exists()
    assert client.get(f"/ai/v1/datasets/{ds}", headers=auth(**ALICE)).status_code == 404


def test_error_contract(client):
    h = auth(**ALICE)
    r = client.post("/ai/v1/datasets/analyze", files={"file": ("a.pdf", b"%PDF", "application/pdf")}, headers=h)
    assert r.status_code == 415 and r.json() == {
        "success": False,
        "message": "Only .csv files are supported.",
        "code": "UNSUPPORTED_MEDIA_TYPE",
    }
    big = b"order_date,revenue\n" + b"2024-01-01,1\n" * 120_000  # > 1 MB test limit
    assert client.post("/ai/v1/datasets/analyze", files={"file": ("b.csv", big, "text/csv")}, headers=h).status_code == 413
    r = client.post("/ai/v1/datasets/analyze", files={"file": ("c.csv", b"foo,bar\n1,2\n3,4\n", "text/csv")}, headers=h)
    assert r.status_code == 422 and "No date column" in r.json()["message"] and r.json()["code"] == "INVALID_DATA"
    assert client.post("/ai/v1/datasets/analyze", files=UPLOAD()).status_code == 401
    assert client.post("/ai/v1/datasets/analyze", headers=h).status_code == 422  # missing file


def test_failed_upload_leaves_no_dataset_behind(client):
    h = auth(user_id="carol", email="c@x.com")
    client.post("/ai/v1/datasets/analyze", files={"file": ("c.csv", b"foo,bar\n1,2\n", "text/csv")}, headers=h)
    assert client.get("/ai/v1/datasets", headers=h).json() == []


def test_cors_only_for_configured_origins(client):
    ok = client.options("/ai/v1/datasets", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    bad = client.options("/ai/v1/datasets", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in bad.headers


def test_fast_phase_under_ten_seconds_for_50k_rows():
    rng = np.random.default_rng(1)
    n = 50_000
    qty = rng.integers(1, 6, n)
    price = rng.uniform(5, 200, n).round(2)
    df = pd.DataFrame(
        {
            "order_id": np.arange(n) // 2,
            "order_date": pd.date_range("2023-01-01", periods=n, freq="15min").strftime("%Y-%m-%d"),
            "customer_id": rng.integers(1, 5000, n),
            "product": rng.integers(1, 200, n).astype(str),
            "category": rng.choice(list("ABCDEF"), n),
            "region": rng.choice(["N", "S", "E", "W"], n),
            "quantity": qty,
            "unit_price": price,
            "cost": (price * 0.6).round(2),
            "revenue": (qty * price).round(2),
        }
    )
    raw = df.to_csv(index=False).encode()
    t0 = time.perf_counter()
    fr = run_fast_phase(raw, "big.csv", "d")
    elapsed = time.perf_counter() - t0
    assert fr.analytics["recordsCount"] == n and elapsed < 10, f"fast phase took {elapsed:.1f}s"
    print(f"\n50k-row fast phase: {elapsed:.2f}s")
