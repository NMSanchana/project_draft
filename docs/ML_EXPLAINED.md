# The ML explained (for a viva, no heavy theory)

Every module returns `{status: ok | unreliable | skipped, reason?, ...}` and a fixed `random_state`, so results are reproducible and
honest about gaps. Code lives in `ai-service/app/ml/` and `ai-service/app/pipeline/`.

---
## 0. Data pipeline: "tidy the shoebox of receipts"
*Idea:* spreadsheets arrive messy. We work out which column is the date/revenue/customer, fix types, drop duplicates, impute gaps,
exclude cancelled/returned orders, and score the data (0-100).
*Quality score* = completeness 40 + uniqueness 15 + validity 25 + coverage 20 (formula in `clean.py`).
*Limits:* roles are guessed from names and values; low confidence is flagged. *Code:* `pipeline/roles.py`, `clean.py`.

## 1. Rule insights: "the owner's checklist"
Fixed thresholds from the teammate's README: growth > +10% (opportunity), decline < -10% (alert), product down > 15%, region up > 20%,
margin < 15%, top-10% customers. *Limit:* thresholds are rules of thumb, not learned. *Code:* `pipeline/rules.py`.

## 2. Forecast "model race" (`pipeline/forecast.py`)
*Analogy:* four weather forecasters predict the next weeks; we test each on the past (hiding the last days, predicting them, scoring
the guess) and trust the best.
*Inputs:* daily revenue (>= 28 days). *Candidates:* seasonal-naive ("same as last week"), Holt-Winters (trend + weekly pattern), SARIMAX,
gradient boosting on lags/calendar. *Selection:* rolling-origin cross-validation (4 folds), lowest sMAPE (symmetric % error).
*Output:* 30 daily forecasts with a 90% interval (from the winner's cross-validation errors, widened for longer horizons), the 30-day
total, the leaderboard. *Honesty:* sMAPE > 30% → `unreliable`; < 28 days → refuses.
*Limits:* the total's interval assumes independent daily errors (slightly optimistic).

## 3. Anomalies with root cause (`pipeline/anomalies.py`)
*Analogy:* a smoke alarm that also tells you which room the smoke is in.
*Steps:* remove the weekday pattern; compare each day with its *local* typical level (29-day rolling median); take the log ratio
(revenue noise is multiplicative); flag only if the **robust z-score** (median/MAD) is >= 4 **and** an **IsolationForest** agrees.
*Root cause:* for a flagged day, per category/region/product/customer, `revenue that day - typical daily revenue`, and the share of the
total deviation; the biggest is named ("West accounts for 101% of the spike").
*Limits:* needs >= 14 days; a real one-day promotion and an error look the same until you check.

## 4. ML Module 1: customer segments + churn (`ml/rfm_churn.py`)
*Analogy:* a shopkeeper who knows the regulars from the drifters, and notices who has gone quiet.
* **Segmentation:** per customer Recency (days since last order), Frequency (orders), Monetary (spend) → log + standardise →
  **K-Means**, k from 3-6 chosen by **silhouette score** → clusters named from centroid ranks (Champions, Loyal, Big Spenders, Promising,
  At Risk, Hibernating).
* **Churn:** "churn" = no purchase in `W` days, `W` = 1.5 x the median gap between a customer's purchases. **No leakage:** the data is
  split at `cutoff = last date - W`; features use only rows <= cutoff, the label uses the days after. Only customers still active at the
  cutoff are modelled. **Logistic regression vs gradient boosting**, best ROC-AUC on a stratified hold-out. The chosen model then scores
  customers as of today. Features include `overdue_ratio` (recency / the customer's own average gap).
* **Fallback:** < 200 modelled customers or one outcome only → a transparent heuristic (`days since last purchase / 2W`), and the output says so.
*Limits:* K-Means assumes round clusters; many customers tie near 100% so the top-10 order among them is arbitrary.

## 5. ML Module 2: "why did revenue change?" (`ml/drivers.py`)
*Analogy:* a detective's report.
* **Layer A, exact decomposition** per segment (category x region): `volume = (Q1/Q0 - 1) q0 p0`, `mix = (q1 - q0 Q1/Q0) p0`,
  `price = (p1 - p0) q1`. These **sum exactly** to the revenue change (unit-tested, including new and discontinued segments).
* **Layer B, ML explanation:** gradient boosting predicts *daily* revenue from calendar + mix shares + price + units; **SHAP** attributes
  the prediction; the average SHAP difference between the two periods ranks the factors. Hold-out R^2 is shown; if poor, trust Layer A.
*Limits:* attribution is not causation; SHAP explains the model, Layer A explains the arithmetic.

## 6. ML Module 3: price elasticity + what-if (`ml/pricing.py`)
*Analogy:* "if I nudge the price, how many customers walk away?"
*Model:* `ln(quantity) = a + b ln(price) + product + month + region effects` (OLS, robust errors). `b` is the **elasticity**: -0.6 = a
+10% price cuts units by ~6% (inelastic); -2 = elastic. Product effects make `b` a *within-product* effect.
*Reliability:* < 100 rows, price barely varies (std of ln price < 0.05 *within product*), p >= 0.05, or a positive `b` → **no number**
("insufficient evidence"). *Simulator:* `units' = Q (1+d)^b`, revenue and profit from the unit cost; range from the 95% CI of `b`;
changes limited to ±20%; also reports the profit-maximising move within ±20%.
*Limits:* observational, not an experiment; extrapolation beyond observed price changes is risky.

## 7. ML Module 4: cross-sell (`ml/basket.py`)
*Analogy:* a shop assistant who knows what goes with what.
*Method:* baskets by order id (else customer + date); **FP-Growth** finds frequent item sets; rules `A -> B` with
**support** (how common), **confidence** (P(B|A)) and **lift** (confidence / P(B); > 1 = together more than chance). Kept: lift > 1.2,
at least 5 co-occurring orders, top 10. One item per order → skipped with the reason.

## 8. RAG: "an open-book exam" (`app/rag/`)
Documents → chunks → embeddings (MiniLM) → Qdrant. A question is embedded, the nearest chunks are fetched (vector search), re-ranked with
BM25 keyword scoring, thresholded, and the answer must come from them, with file/page citations. Nothing relevant → "I couldn't find
that". *Limits:* thresholds not calibrated on a labelled corpus; PDFs must contain text (no OCR).

## 9. Chat agent: "exact numbers, never invented" (`app/chat/`)
The language model (if used at all) only fills in a **form** (a JSON query plan). The form is checked against a closed schema and run by
fixed, whitelisted pandas code. The words around the numbers come from templates. See `ARCHITECTURE.md` section 5.
