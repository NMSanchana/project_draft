# Viva Q&A (32 likely questions)

### Architecture and decisions
**1. Why a separate Python service instead of extending the Nest backend?** The Nest/Mongo/auth work was finished and frozen; Python has
the right libraries (pandas, scikit-learn, statsmodels, SHAP); and the two halves can be developed, run and assessed independently.
They share only the JWT secret.

**2. How does the AI service know who the user is without a user table?** It verifies the HS256 token Nest issued (same secret, `exp`
required) and reads `id`/`email` from the claims. Every dataset, conversation, document and vector collection is scoped to that id.

**3. Why SQLite and not MongoDB?** The constraint was "no new Mongo usage". SQLite needs no installation, keeps results in one file, and
is fine for a single-instance project. For scale I would move to Postgres + object storage + a job queue.

**4. Why local LLM, local vector DB, local embeddings?** Privacy (business data never leaves the machine), no cost, and it demonstrates
the full stack. Trade-off: a 3B model is less fluent, so the design never depends on it for correctness.

**5. Why two phases on upload?** The dashboard must fill instantly (about 1 s), but forecasting, ML and LLM text take longer. Fast phase returns
the exact `ProcessedAnalytics`; enrichment runs in the background and the UI polls.

**6. What if a module fails?** Each stage is isolated; failure is recorded and the others continue. Every module returns
`ok | unreliable | skipped` plus a reason, which the UI/chat/PDF show.

### Data
**7. How do you detect columns when every CSV is different?** Name score (exact, head-noun, fuzzy) + value score (dates parse, cardinality,
integer-ness), then a greedy one-to-one assignment with a confidence per role. Verified on three different schemas.

**8. What is the per-unit cost issue?** The sample files store cost per unit. Subtracting it from line revenue gives wrong margins. The
cleaner checks whether `cost <= unit price` on multi-unit rows and converts to line cost; the report states which basis was used.

**9. How is data quality scored?** 0-100 = completeness 40 + uniqueness 15 + validity 25 + coverage 20 (formula in `clean.py`).

### ML
**10. Why K-Means for segments?** Simple, fast, explainable with centroids, and standard for RFM. k is chosen by silhouette over 3-6.
Limitation: assumes roughly round clusters; I log-transform and scale to reduce skew.

**11. How do you prevent data leakage in churn?** A time split: features come only from rows on/before the cutoff, labels from the window
after it. A unit test mutates post-cutoff data and asserts the features do not change.

**12. How is churn defined?** No purchase within `W` days, with `W` = 1.5 x the median gap between purchases (clamped), so it adapts
to each business. Only customers still active at the cutoff are modelled, otherwise the task is trivial.

**13. Which churn model and why?** Logistic regression (interpretable baseline) vs gradient boosting, chosen by hold-out ROC-AUC. With
fewer than 200 modelled customers I fall back to a transparent heuristic and say so.

**14. How does the decomposition sum exactly to the change?** Algebra: `V + M + P = (q1-q0)p0 + (p1-p0)q1 = R1 - R0` per segment, with
new/discontinued segments handled so the identity still holds. It is unit-tested.

**15. What does SHAP add if the decomposition is exact?** The decomposition explains the arithmetic (price/volume/mix by segment); SHAP
explains what a model learned about daily revenue drivers (weekday, mix shares, units). R^2 is reported; if low, only Layer A is trusted.

**16. What is elasticity and how do you estimate it?** The % change in units for a 1% price change, from a log-log regression with product,
month and region controls (robust errors). -0.6 is inelastic, -2 elastic.

**17. When do you refuse to give an elasticity?** Too few rows, prices barely vary within a product, not significant (p >= 0.05), or a
positive sign (confounded). The simulator then returns *no numbers*.

**18. Isn't observational elasticity biased?** Yes, it measures association, not a controlled experiment. Controls reduce, not remove, the
bias; that is why results carry confidence intervals, a reliability flag and a ±20% cap.

**19. How does market-basket analysis work?** FP-Growth finds frequent item sets; rules are scored by support, confidence and lift
(confidence / base rate). I keep lift > 1.2 with at least 5 co-occurrences. One item per order means no rules.

**20. How do you choose the forecasting model?** A "race": rolling-origin cross-validation over four candidates, lowest sMAPE wins. If
history is under 28 days I refuse; if the best sMAPE exceeds 30% it is labelled unreliable.

**21. How do you detect anomalies and find the cause?** Weekday-adjust, compare to a local rolling median, log ratio, flag only when a robust
z-score >= 4 and IsolationForest agree. For each flagged day I compute which category/region/customer explains the deviation.

**22. Why did you change the anomaly threshold between milestones?** First 3.5, then 3.0 when a planted -78% dip scored 3.49 on the raw
scale. After moving to a log ratio against a local level, planted events score |z| 8-11 and natural low days 3-5, so 4.0 is both sensitive
and strict. (It is tuned on synthetic data; I say so.)

### RAG and chat
**23. What is RAG and why use it?** Retrieval-Augmented Generation: fetch relevant text first, answer only from it. It grounds answers in
the user's documents and gives citations instead of relying on the model's memory.

**24. How is the answer grounded?** Retrieved chunks only; an LLM answer is discarded unless every number appears in the excerpts; if
nothing passes the thresholds the system says it could not find it. Sources are returned with file and page.

**25. Why vector search plus BM25?** Embeddings capture meaning (paraphrase), BM25 captures exact keywords (numbers, names). Combining
them (0.6/0.4) is more robust than either alone.

**26. How do you stop one user reading another's documents?** Separate Qdrant collections per user and per dataset; the retriever only
queries `kb_shared`, the caller's own collection and the active dataset's. A test checks user B never retrieves user A's text.

**27. How does the chat give exact numbers and avoid hallucination?** The model never writes numbers or code. A question becomes a JSON
query plan, validated against a closed schema, executed by whitelisted pandas code; the words come from templates. 31 question/number
pairs are tested against independent pandas results.

**28. What about prompt injection?** Three layers: a guard refuses override/code-execution requests; uploaded-document lines that look like
instructions are stripped before reaching the model and the prompt calls them untrusted; plan output is schema-validated so even a
manipulated model cannot execute anything.

**29. What works without Ollama?** Everything except fluent phrasing: the rule planner answers data questions instantly; ML answers are
template-built from module output; documents show the most relevant passages; narrative insights fall back to deterministic templates.

### Quality and honesty
**30. How did you test it?** 250 automated tests (security, role detection on 3 schemas, golden KPIs vs pandas, rules at their thresholds,
forecasts, anomalies with planted events, each ML module with planted ground truth, RAG with an in-memory Qdrant, chat, API, PDF).
Planted-pattern data: elasticities recovered within tolerance, the stopping customers ranked at the top, the South decline found.

**31. What could not be tested here?** The real MiniLM model, a real Qdrant server, a real Ollama LLM, Nest + MongoDB together, and a browser
click-through (see `VERIFICATION_REPORT.md`). The pipeline was tested with an in-memory Qdrant and a deterministic fake embedder.

**32. Limitations and future work?** Single instance; retrieval thresholds uncalibrated on a labelled corpus; elasticity is observational;
no OCR for scanned PDFs; roles are heuristic. Future: Postgres + job queue, per-product forecasts, uplift/A-B tests for pricing, a calibrated
RAG evaluation set, streaming chat, signed-URL report downloads.
