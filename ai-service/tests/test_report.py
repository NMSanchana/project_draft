import io

import pytest
from pypdf import PdfReader

from app.llm import ollama_client
from app.pipeline import stages
from app.pipeline.assemble import run_fast_phase
from app.pipeline.enrichment import EnrichmentContext
from app.reports.pdf import build_report
from tests.conftest import SAMPLE_DIR, auth

ALICE = dict(user_id="alice-r", email="a@x.com")


def _text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def _ctx(name):
    ollama_client.is_available = lambda: False
    fr = run_fast_phase((SAMPLE_DIR / name).read_bytes(), name, "r")
    c = EnrichmentContext("r", "u", fr.clean_df, fr.analytics)
    for _, fn in stages.DEFAULT_STAGES[:-2]:
        fn(c)
    return c


@pytest.mark.parametrize("name", ["sample_ecommerce.csv", "technova_electronics_sales.csv", "retail_with_orders.csv"])
def test_pdf_generates_for_every_sample_with_all_sections(name):
    c = _ctx(name)
    pdf = build_report(
        name,
        c.analytics,
        c.modules,
        [{"fileName": "business_policy.md", "scope": "shared", "shared": True, "chunks": 5}],
        ["business_policy.md"],
    )
    assert pdf[:5] == b"%PDF-" and len(pdf) > 20_000
    text = _text(pdf)
    for h in (
        "Business Insight Report",
        "1. Data quality",
        "2. Key metrics",
        "3. Revenue trend",
        "4. Insights",
        "5. Forecast",
        "6. Anomalies",
        "7. Customer segments",
        "8. Why did revenue change",
        "9. Price elasticity",
        "10. Cross-sell",
        "11. Documents",
    ):
        assert h in text, h
    assert f"${c.analytics['revenue']:,.0f}" in text.replace("\n", " ")
    assert "business_policy.md" in text and "Page 2" in text


def test_skipped_modules_are_listed_with_their_reason():
    c = _ctx("sample_ecommerce.csv")  # one item per order -> no cross-sell rules
    text = _text(build_report("s.csv", c.analytics, c.modules)).replace("\n", " ")
    assert "Not available:" in text and ("one item per order" in text or "cross-sell" in text.lower())
    c.modules["forecast"] = {"status": "skipped", "reason": "Need at least 28 days of history to forecast reliably (found 9)."}
    text2 = _text(build_report("s.csv", c.analytics, c.modules)).replace("\n", " ")
    assert "Need at least 28 days of history" in text2 and "forecast" in text2.split("Not available in this report:")[1][:80]


def test_one_broken_section_does_not_break_the_report():
    c = _ctx("sample_ecommerce.csv")
    c.modules["anomalies"] = {"status": "ok", "anomalies": [{"oops": 1}], "method": "x", "days_analyzed": 3, "count": 1}  # malformed
    text = _text(build_report("s.csv", c.analytics, c.modules)).replace("\n", " ")
    assert "could not be rendered" in text and "7. Customer segments" in text and "8. Why did revenue change" in text


def test_report_endpoint(client, monkeypatch):
    monkeypatch.setattr(ollama_client, "is_available", lambda: False)
    h = auth(**ALICE)
    p = SAMPLE_DIR / "technova_electronics_sales.csv"
    ds = client.post("/ai/v1/datasets/analyze", files={"file": (p.name, p.read_bytes(), "text/csv")}, headers=h).json()["datasetId"]
    r = client.get(f"/ai/v1/datasets/{ds}/report.pdf", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith('attachment; filename="insight-report-technova_electronics_sales')
    assert r.content[:5] == b"%PDF-" and "Business Insight Report" in _text(r.content)
    assert client.get(f"/ai/v1/datasets/{ds}/report.pdf").status_code == 401
    assert client.get(f"/ai/v1/datasets/{ds}/report.pdf", headers=auth(user_id="mallory", email="m@x.com")).status_code == 403
    assert client.get("/ai/v1/datasets/nope/report.pdf", headers=h).status_code == 404


def test_report_is_409_while_enriching(client):
    from app.db import session_scope
    from app.models import Dataset

    p = SAMPLE_DIR / "sample_ecommerce.csv"
    h = auth(**ALICE)
    ds = client.post("/ai/v1/datasets/analyze", files={"file": (p.name, p.read_bytes(), "text/csv")}, headers=h).json()["datasetId"]
    db = session_scope()
    db.get(Dataset, ds).status = "enriching"
    db.commit()
    db.close()
    r = client.get(f"/ai/v1/datasets/{ds}/report.pdf", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "NOT_READY"
