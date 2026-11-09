import pytest

from tests.conftest import SAMPLE_DIR, auth
from tests.synth_ml import make_baskets, make_pricing

ALICE = dict(user_id="alice-ml", email="a@x.com")
H = lambda: auth(**ALICE)  # noqa: E731


def _csv(df, rename):
    return df.rename(columns=rename).to_csv(index=False).encode()


def _upload(client, payload: bytes, name="data.csv", headers=None):
    r = client.post("/ai/v1/datasets/analyze", files={"file": (name, payload, "text/csv")}, headers=headers or H())
    assert r.status_code == 200, r.text
    return r.json()["datasetId"]


@pytest.fixture(scope="module")
def pricing_ds(client_module):
    c = client_module
    return c, _upload(c, _csv(make_pricing(), {"date": "order_date", "customer": "customer_id", "unit_price": "price"}))


@pytest.fixture(scope="module")
def client_module(_env):
    from fastapi.testclient import TestClient

    from app.db import init_db, init_engine
    from app.main import create_app

    init_engine()
    init_db()
    with TestClient(create_app()) as c:
        yield c


def test_full_pipeline_exposes_all_ml_modules_and_insights(pricing_ds):
    c, ds = pricing_ds
    got = c.get(f"/ai/v1/datasets/{ds}", headers=H()).json()
    assert got["status"] == "ready"
    ids = [i["id"] for i in got["insights"]]
    assert len(ids) == len(set(ids))
    assert any(i.startswith("ml-pricing") for i in ids) and any(i.startswith("ml-drivers") for i in ids)
    for i in got["insights"]:
        assert i["type"] in {"growth", "alert", "opportunity", "info"} and i["title"] and i["desc"] is not None
    ml = got["ml"]
    assert ml["pricing"]["status"] == "ok" and {r["segment"] for r in ml["pricing"]["reliable_segments"]} >= {"Elastic", "Inelastic"}
    assert ml["drivers"]["reconciles"] is True
    bk = ml["basket"]  # random co-purchasing (customer+date baskets): no strong rule may be invented
    assert bk["status"] in ("ok", "skipped") and (bk.get("top_rule") is None or bk["top_rule"]["lift"] < 1.5)
    for m in ("segments", "churn", "drivers", "pricing", "basket", "forecast", "anomalies"):
        d = c.get(f"/ai/v1/datasets/{ds}/ml/{m}", headers=H()).json()
        assert d["status"] in ("ok", "unreliable", "skipped"), (m, d)


def test_simulate_endpoint(pricing_ds):
    c, ds = pricing_ds
    r = c.post("/ai/v1/pricing/simulate", json={"datasetId": ds, "segmentValue": "Elastic", "priceChangePct": 5}, headers=H())
    assert r.status_code == 200
    b = r.json()
    assert b["reliable"] and b["revenue_delta"] < 0 and b["profit_delta_range"][0] <= b["profit_delta"] <= b["profit_delta_range"][1]
    u = c.post("/ai/v1/pricing/simulate", json={"datasetId": ds, "segmentValue": "Fixed", "priceChangePct": 5}, headers=H()).json()
    assert u["reliable"] is False and "revenue_delta" not in u


def test_simulate_endpoint_errors(pricing_ds):
    c, ds = pricing_ds
    post = lambda body, h=None: c.post("/ai/v1/pricing/simulate", json=body, headers=h or H())  # noqa: E731
    r = post({"datasetId": ds, "segmentValue": "Elastic", "priceChangePct": 35})
    assert r.status_code == 422 and r.json()["success"] is False
    r = post({"datasetId": ds, "segmentValue": "Gadgets", "priceChangePct": 5})
    assert r.status_code == 422 and r.json()["code"] == "UNKNOWN_SEGMENT" and "Elastic" in r.json()["message"]
    assert (
        post({"datasetId": ds, "segmentValue": "Elastic", "priceChangePct": 5}, auth(user_id="mallory", email="m@x.com")).status_code == 403
    )
    assert post({"datasetId": "nope", "segmentValue": "x", "priceChangePct": 1}).status_code == 404
    assert c.post("/ai/v1/pricing/simulate", json={"datasetId": ds, "segmentValue": "Elastic", "priceChangePct": 1}).status_code == 401


def test_basket_and_segments_through_the_api(client_module):
    c = client_module
    ds = _upload(c, _csv(make_baskets(), {"date": "order_date", "customer": "customer_id"}))
    ml = c.get(f"/ai/v1/datasets/{ds}", headers=H()).json()["ml"]
    assert ml["basket"]["status"] == "ok" and ml["basket"]["top_rule"]["lift"] > 1.5
    top = c.get(f"/ai/v1/datasets/{ds}/ml/basket", headers=H()).json()["rules"][0]
    assert {top["antecedent"], top["consequent"]} in ({"Monitor", "HDMI Cable"}, {"Laptop", "Mouse"})


@pytest.mark.parametrize("name", ["sample_ecommerce.csv", "technova_electronics_sales.csv"])
def test_real_sample_csvs_run_every_module_without_failure(client_module, name):
    c = client_module
    ds = _upload(c, (SAMPLE_DIR / name).read_bytes(), name)
    got = c.get(f"/ai/v1/datasets/{ds}", headers=H()).json()
    assert got["status"] == "ready"
    for m in ("forecast", "anomalies", "segments", "churn", "drivers", "pricing", "basket"):
        d = c.get(f"/ai/v1/datasets/{ds}/ml/{m}", headers=H()).json()
        assert d["status"] in ("ok", "unreliable", "skipped"), (m, d)
        assert d["status"] != "skipped" or d.get("reason")  # skipped always says why
    ids = [i["id"] for i in got["insights"]]
    assert len(ids) == len(set(ids)) and any(i.startswith("ml-drivers") for i in ids)
    assert any(i.startswith("ml-basket") for i in ids)  # single-item orders -> explicit "no rules" insight
