import pandas as pd
import pytest

from app.pipeline.anomalies import anomaly_insights, run_anomalies
from app.pipeline.forecast import forecast_insight, run_forecast
from tests.synth import make_sales, spike_date

DF = make_sales()


@pytest.fixture(scope="module")
def fc():
    return run_forecast(DF)


def test_forecast_races_all_four_models_and_picks_by_cv(fc):
    assert fc["status"] in ("ok", "unreliable")
    names = {b["model"] for b in fc["leaderboard"]}
    assert names == {"Seasonal Naive", "Holt-Winters", "SARIMAX", "Gradient Boosting"}
    ok = [b for b in fc["leaderboard"] if b["status"] == "ok"]
    assert fc["winner"] == ok[0]["model"] and fc["winner_smape"] == ok[0]["smape"]  # leaderboard sorted by sMAPE
    assert fc["cv"]["folds"] >= 3


def test_forecast_beats_seasonal_naive_on_seasonal_data(fc):
    naive = next(b for b in fc["leaderboard"] if b["model"] == "Seasonal Naive")
    assert fc["beats_seasonal_naive"] and (fc["winner"] == "Seasonal Naive" or fc["winner_smape"] < naive["smape"])
    assert fc["status"] == "ok" and fc["winner_smape"] < 25


def test_prediction_intervals_ordered_and_contain_point(fc):
    assert len(fc["daily"]) == 30
    for d in fc["daily"]:
        assert 0 <= d["lower"] <= d["forecast"] <= d["upper"]
    t = fc["next_30_days"]
    assert t["lower"] <= t["total"] <= t["upper"]
    assert t["total"] == pytest.approx(sum(d["forecast"] for d in fc["daily"]), rel=1e-3)
    widths = [d["upper"] - d["lower"] for d in fc["daily"]]
    assert widths[-1] >= widths[0]  # uncertainty grows with horizon


def test_forecast_is_reproducible():
    a, b = run_forecast(DF)["next_30_days"], run_forecast(DF)["next_30_days"]
    assert a == b


def test_forecast_refuses_short_history_instead_of_fabricating():
    short = DF[DF["date"] < DF["date"].min() + pd.Timedelta(days=20)]
    r = run_forecast(short)
    assert r["status"] == "skipped" and "28 days" in r["reason"] and "daily" not in r
    assert forecast_insight(r) is None


def test_forecast_insight_text_has_range_and_model(fc):
    i = forecast_insight(fc)
    assert i["id"] == "ml-forecast-1" and i["title"].startswith("Forecast:")
    assert fc["winner"] in i["desc"] and "90% range" in i["desc"] and "sMAPE" in i["desc"]


# ---------------------------------------------------------------- anomalies
@pytest.fixture(scope="module")
def an():
    return run_anomalies(DF)


def test_planted_spike_and_dip_are_found(an):
    by_date = {a["date"]: a for a in an["anomalies"]}
    assert spike_date() in by_date and by_date[spike_date()]["direction"] == "spike"
    dip = spike_date(day=140)
    assert dip in by_date and by_date[dip]["direction"] == "dip"
    assert an["count"] <= 6  # not flagging 5-10% of days like contamination alone would


def test_root_cause_names_planted_category_and_region(an):
    spike = next(a for a in an["anomalies"] if a["date"] == spike_date())
    dims = {c["dimension"]: c for c in spike["causes"]}
    assert dims["category"]["value"] == "Electronics" and dims["region"]["value"] == "West"
    assert dims["category"]["share_pct"] > 60
    assert "Electronics" in spike["cause_text"] or "West" in spike["cause_text"]


def test_both_detectors_must_agree_no_false_alarms_on_clean_data():
    clean = make_sales(spike_day=None, dip_day=None)
    assert run_anomalies(clean)["count"] <= 1


def test_anomaly_skip_and_insights():
    assert run_anomalies(DF[DF["date"] < DF["date"].min() + pd.Timedelta(days=9)])["status"] == "skipped"
    ins = anomaly_insights(run_anomalies(DF))
    assert ins and all(i["id"].startswith("ml-anomaly-") for i in ins)
    assert any(i["type"] == "alert" for i in ins) and "Anomaly:" in ins[0]["title"]
