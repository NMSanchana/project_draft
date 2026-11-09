"""Forecast "model race" on the daily revenue series.

Candidates: seasonal-naive (weekly), Holt-Winters, SARIMAX, and gradient boosting on lag/calendar
features. The winner is chosen by **rolling-origin cross-validation** (lowest sMAPE, MAE as tie-break).

Prediction intervals (90%) come from the pooled cross-validation residuals of the *winning* model,
widened by sqrt(step / CV-horizon) beyond the CV horizon. The 30-day total's interval assumes errors
are independent across days, which slightly understates uncertainty (documented limitation).
Refuses (status ``skipped``) when there is too little history instead of inventing a number.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

MIN_DAYS = 28
HORIZON = 30
MAX_HISTORY = 365
Z90 = 1.645
UNRELIABLE_SMAPE = 30.0


def daily_series(df: pd.DataFrame, max_days: int = MAX_HISTORY) -> pd.Series:
    s = df.groupby(df["date"].dt.normalize())["revenue"].sum()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"), fill_value=0.0)
    return s.tail(max_days)


# ----------------------------------------------------------------------------- candidates
Model = Callable[[np.ndarray, pd.DatetimeIndex, int], np.ndarray]


def _seasonal_naive(train: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    last = train[-7:] if len(train) >= 7 else np.full(7, train.mean())
    return np.array([last[i % 7] for i in range(h)], dtype=float)


def _holt_winters(train: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    seasonal = len(train) >= 14  # needs >= 2 full weekly cycles
    m = ExponentialSmoothing(
        train,
        trend="add",
        damped_trend=True,
        seasonal="add" if seasonal else None,
        seasonal_periods=7 if seasonal else None,
        initialization_method="estimated",
    ).fit()
    return np.asarray(m.forecast(h), dtype=float)


def _sarimax(train: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    seas = (1, 0, 0, 7) if len(train) >= 28 else (0, 0, 0, 0)
    m = SARIMAX(train, order=(1, 1, 1), seasonal_order=seas, enforce_stationarity=False, enforce_invertibility=False).fit(
        disp=False, maxiter=50
    )
    return np.asarray(m.forecast(h), dtype=float)


def _gb_row(hist: list[float], date: pd.Timestamp) -> tuple[list[float], float]:
    base = max(float(np.mean(hist[-28:])), 1e-9)
    lag1, lag7 = hist[-1], hist[-7]
    return [date.dayofweek, date.day, lag1 / base, lag7 / base, float(np.mean(hist[-7:])) / base], base


def _gradient_boosting(train: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    """Predict revenue as a ratio to the trailing-28-day mean (so level shifts are handled)."""
    if len(train) < 21:
        raise ValueError("needs at least 21 days")
    hist = [float(v) for v in train]
    X, y = [], []
    for i in range(14, len(hist)):
        row, base = _gb_row(hist[:i], dates[i])
        X.append(row)
        y.append(hist[i] / base)
    gb = GradientBoostingRegressor(n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=42)
    gb.fit(np.array(X), np.array(y))
    out = []
    for k in range(h):
        d = dates[-1] + pd.Timedelta(days=k + 1)
        row, base = _gb_row(hist, d)
        pred = float(gb.predict(np.array([row]))[0]) * base
        hist.append(pred)
        out.append(pred)
    return np.array(out)


CANDIDATES: dict[str, Model] = {
    "Seasonal Naive": _seasonal_naive,
    "Holt-Winters": _holt_winters,
    "SARIMAX": _sarimax,
    "Gradient Boosting": _gradient_boosting,
}


# ----------------------------------------------------------------------------- evaluation
def _smape(actual: np.ndarray, pred: np.ndarray) -> float:
    denom = np.abs(actual) + np.abs(pred)
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(denom == 0, 0.0, 2 * np.abs(actual - pred) / denom)
    return float(100 * v.mean())


def _origins(n: int, h: int, folds: int = 4) -> list[int]:
    start = max(21, n // 2)
    last = n - h
    if last < start:
        start = max(14, last)
    return sorted({int(o) for o in np.linspace(start, last, num=folds)}) if last >= 14 else []


def _cv(series: pd.Series, fn: Model, origins: list[int], h: int) -> dict:
    vals, idx = series.values.astype(float), series.index
    maes, preds, acts, res = [], [], [], []
    for o in origins:
        p = fn(vals[:o], idx[:o], h)
        a = vals[o : o + h]
        p = p[: len(a)]
        maes.append(float(np.mean(np.abs(a - p))))
        preds.append(p)
        acts.append(a)
        res.append(a - p)
    A, P = np.concatenate(acts), np.concatenate(preds)
    return {"mae": float(np.mean(maes)), "smape": _smape(A, P), "residuals": np.concatenate(res)}


def run_forecast(df: pd.DataFrame, horizon: int = HORIZON) -> dict:
    """Return the forecast module result (``status`` = ok | unreliable | skipped)."""
    s = daily_series(df)
    n = len(s)
    if n < MIN_DAYS:
        return {"status": "skipped", "reason": f"Need at least {MIN_DAYS} days of history to forecast reliably (found {n})."}
    h_cv = int(min(14, max(7, n // 8)))
    origins = _origins(n, h_cv)
    if not origins:
        return {"status": "skipped", "reason": "Not enough history for cross-validation."}

    board, cv_res = [], {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, fn in CANDIDATES.items():
            try:
                r = _cv(s, fn, origins, h_cv)
                cv_res[name] = r
                board.append({"model": name, "mae": round(r["mae"], 2), "smape": round(r["smape"], 2), "status": "ok"})
            except Exception as exc:  # noqa: BLE001 - a failing candidate must not stop the race
                board.append({"model": name, "mae": None, "smape": None, "status": f"failed: {str(exc)[:80]}"})
        if not cv_res:
            return {"status": "skipped", "reason": "No forecasting model could be fitted on this data."}
        winner = min(cv_res, key=lambda k: (cv_res[k]["smape"], cv_res[k]["mae"]))
        board.sort(key=lambda b: (b["smape"] is None, b["smape"] if b["smape"] is not None else 0))
        point = np.clip(CANDIDATES[winner](s.values.astype(float), s.index, horizon), 0, None)

    res = cv_res[winner]["residuals"]
    q_lo, q_hi = min(np.quantile(res, 0.05), 0.0), max(np.quantile(res, 0.95), 0.0)
    steps = np.arange(1, horizon + 1)
    scale = np.maximum(1.0, np.sqrt(steps / h_cv))
    lower = np.clip(point + q_lo * scale, 0, None)
    upper = point + q_hi * scale
    lower, upper = np.minimum(lower, point), np.maximum(upper, point)

    sigma_i = (upper - lower) / (2 * Z90)
    sigma_tot = float(np.sqrt(np.sum(sigma_i**2)))
    total = float(point.sum())
    tot_lo, tot_hi = max(0.0, total - Z90 * sigma_tot), total + Z90 * sigma_tot

    future = pd.date_range(s.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")
    naive = cv_res.get("Seasonal Naive")
    win_smape = cv_res[winner]["smape"]
    last30 = float(s.tail(30).sum())
    status = "ok" if win_smape <= UNRELIABLE_SMAPE else "unreliable"
    out = {
        "status": status,
        "winner": winner,
        "winner_smape": round(win_smape, 2),
        "winner_mae": round(cv_res[winner]["mae"], 2),
        "beats_seasonal_naive": bool(naive is None or win_smape < naive["smape"] or winner == "Seasonal Naive"),
        "leaderboard": board,
        "cv": {"folds": len(origins), "horizon_days": h_cv, "history_days": n},
        "interval_level": 0.90,
        "horizon_days": horizon,
        "daily": [
            {"date": d.strftime("%Y-%m-%d"), "forecast": round(float(p), 2), "lower": round(float(lo), 2), "upper": round(float(hi), 2)}
            for d, p, lo, hi in zip(future, point, lower, upper)
        ],
        "next_7_days": round(float(point[:7].sum()), 2),
        "next_30_days": {"total": round(total, 2), "lower": round(tot_lo, 2), "upper": round(tot_hi, 2)},
        "last_30_days_actual": round(last30, 2),
        "projected_change_pct": round(100 * (total - last30) / last30, 1) if last30 > 0 else None,
        "history_tail": [{"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 2)} for d, v in s.tail(60).items()],
    }
    if status == "unreliable":
        out["reason"] = f"Best model still has a high error (sMAPE {win_smape:.0f}%); treat the forecast as indicative only."
    return out


def forecast_insight(fc: dict) -> dict | None:
    """One ``RuleInsight`` summarising the forecast (None when skipped)."""
    if fc.get("status") not in ("ok", "unreliable"):
        return None
    t = fc["next_30_days"]
    ch = fc.get("projected_change_pct")
    itype, sev = "info", "Info"
    if fc["status"] == "ok" and ch is not None and ch <= -10:  # never raise alarms on an unreliable forecast
        itype, sev = "alert", "Medium"
    elif fc["status"] == "ok" and ch is not None and ch >= 10:
        itype, sev = "growth", "Low"
    trend = f" That is {ch:+.1f}% versus the last 30 days." if ch is not None else ""
    rec = (
        "Treat this as indicative: forecast error is high."
        if fc["status"] == "unreliable"
        else "Plan inventory and staffing around the projected range, not just the point estimate."
    )
    return {
        "id": "ml-forecast-1",
        "type": itype,
        "severity": sev,
        "title": f"Forecast: next 30 days ≈ ${t['total']:,.0f}",
        "desc": (
            f"Projected revenue for the next 30 days is ≈ ${t['total']:,.0f} (90% range ${t['lower']:,.0f} to "
            f"${t['upper']:,.0f}). Best model: {fc['winner']} (sMAPE {fc['winner_smape']:.1f}%).{trend}"
        ),
        "recommendation": rec,
    }
