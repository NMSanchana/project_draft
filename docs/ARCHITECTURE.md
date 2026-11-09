# Architecture

## 1. The big picture

```mermaid
flowchart LR
  subgraph Browser
    FE["Next.js frontend :3000<br/>(UI unchanged; 3 wiring files)"]
  end
  FE -- "register / login / profile" --> NEST["NestJS :5000<br/>auth only"]
  NEST --> MONGO[("MongoDB<br/>users")]
  FE -- "upload / poll / chat / report<br/>Authorization: Bearer JWT" --> AI["FastAPI AI service :8000"]
  AI --> SQL[("SQLite<br/>datasets, results, chat")]
  AI --> FS[("uploads + cleaned parquet")]
  AI --> QD[("Qdrant :6333<br/>vectors")]
  AI --> OL["Ollama :11434<br/>local LLM"]
  AI -. "embeddings (in-process)" .- EMB["MiniLM 384-d"]
```

**Why a "sidecar" service?** The teammate's NestJS + MongoDB + UI are a finished, separate piece of work. Putting all the data science
in a *separate Python service* means (a) zero changes to the frozen backend, (b) the right language for the job (pandas, scikit-learn,
statsmodels, SHAP), (c) the two halves can be shown, run and graded independently. The only thing they share is the **JWT secret**:
Nest signs the login token (HS256), the AI service verifies it with the same secret. No user table exists in the AI service.

**Trade-offs.** The browser talks to two servers (needs CORS and two base URLs); the AI service is stateful (SQLite + files), so it runs
as a single instance; local LLMs are slower and less fluent than hosted ones. In exchange: nothing leaves the machine, and there is no
API cost or key.

## 2. Upload: two phases

```mermaid
sequenceDiagram
  participant B as Browser
  participant A as AI service
  participant DB as SQLite/files
  B->>A: POST /datasets/analyze (CSV)
  Note over A: FAST PHASE (about 1 s for 25k rows)<br/>ingest, detect roles, clean, KPIs,<br/>trend bars, rule insights
  A->>DB: save result + cleaned parquet (status=enriching)
  A-->>B: full ProcessedAnalytics (dashboard renders now)
  A->>A: background ENRICHMENT, one stage at a time
  Note over A: forecast, anomalies, segments+churn,<br/>drivers, pricing, cross-sell, narrative, vector index
  loop every 3 s (browser)
    B->>A: GET /datasets/{id}
    A-->>B: status enriching and more insights, then ready
  end
```

* **Fast phase** returns exactly the object the dashboard already consumes (`ProcessedAnalytics`), so the UI fills in immediately.
* **Enrichment** runs stage by stage; after each stage the result is saved, so insights appear progressively.
  A stage that throws is recorded (`{"status": "failed"}`) and the rest continue: **one failing module never fails the dataset**.
* Every ML module returns `status: ok | unreliable | skipped` plus a `reason`, so gaps are explained, never hidden.

## 3. Data pipeline (`app/pipeline/`)

`ingest.py` (encoding, delimiter, headers) → `roles.py` (what each column *is*) → `clean.py` (typed canonical frame + cleaning report +
quality score) → `kpis.py` → `trend.py` (bars in the exact `TrendBarItem` shape) → `rules.py` (README insight catalog) → `assemble.py`.

* **Role detection** scores each column against each role: 75% name match (exact / head-noun / fuzzy: `product_category` is a *category*,
  `customer_id` a *customer*) + 25% value check (dates parse, order ids are mostly unique, regions have low cardinality). A greedy
  one-to-one assignment gives every role a confidence that is shown to the user.
* **Per-unit cost.** Many CSVs store unit cost. The cleaner tests whether `cost <= unit price` on multi-unit rows and converts to line cost
  when needed. (Both original sample files are per-unit; the draft code mixed it with line revenue and produced wrong margins.)

## 4. RAG (`app/rag/`)

```mermaid
flowchart TD
  D["PDF / TXT / MD<br/>(knowledge_base/ or upload)"] --> X["extract text per page (pypdf)"]
  X --> C["chunk ~750 chars, ~100 overlap,<br/>sentence-aware, never across pages"]
  C --> E["embed: all-MiniLM-L6-v2 (384-d)"]
  E --> Q[("Qdrant")]
  F["dataset facts after analysis<br/>(KPIs, insights, segments, drivers ...)"] --> E
  U["question"] --> QE["embed query"] --> S["query_points on 3 collections:<br/>kb_shared + kb_USER + data_DATASET"]
  S --> R["BM25 re-rank<br/>combined = 0.6 cosine + 0.4 bm25"] --> T["thresholds: cosine >= 0.20 and combined >= 0.30"]
  T --> A["answer + citations<br/>(or 'could not find')"]
```

* **Isolation by collection:** `kb_<userId>` (private), `kb_shared` (the `knowledge_base/` folder, readable by all), `data_<datasetId>`
  (facts + dataset-scoped uploads; deleted with the dataset). Another user's collection is simply never queried.
* **Idempotent:** content hash per (owner, scope); an edited shared file replaces its old vectors; deleted files are removed.
* **Grounded:** an LLM answer is discarded unless every number in it appears in the retrieved excerpts; document text is sanitised
  (instruction-like lines removed) and the prompt declares it untrusted data.
* **Graceful degradation:** Qdrant down → chat says document search is unavailable but still answers data questions; embedding model not
  loadable → HTTP 503 with an actionable message; no Ollama → the most relevant passages are shown with a note.

## 5. Chat agent (`app/chat/`)

```mermaid
flowchart TD
  M["message"] --> G{"injection / code<br/>request?"}
  G -- yes --> REF["refuse"]
  G -- no --> RT["intent router (keyword rules;<br/>LLM only if no rule matches)"]
  RT --> DQ["data_query"] --> PL["rule planner (instant)<br/>else LLM -> JSON plan"] --> V["strict pydantic schema<br/>+ real values resolved"] --> EX["whitelisted pandas executor"] --> CP["composer: plain text,<br/>numbers from executor only"]
  RT --> ML["ml_insight"] --> MA["answers built from stored module output<br/>(drivers/pricing may recompute for the asked month / %)"]
  RT --> DOC["document_question"] --> RAG["retrieve -> grounded answer + citations"]
  RT --> ST["smalltalk / help"]
```

The model **never writes code and never supplies a number**. A *query plan* is data (operation, metric, group_by, filters, time range,
top_n, sort) validated against a closed schema; unknown columns, operations or extra fields are rejected before anything runs.
Follow-ups ("and for the West region?") reuse the previous plan stored per conversation.

## 6. Security model

* JWT (HS256, shared secret, `exp` required) on every route except `/health`; identity = token claims; every row/vector is scoped to the
  token's user id; another user's dataset → 403.
* Upload limits (type, size), sanitised file names, parameterised ORM queries, CORS restricted to configured origins.
* No `eval`/`exec`; prompt-injection guard on user text; retrieved text sanitised; dataset text sanitised before entering any prompt.
* No external network calls at runtime (one-time model downloads only).

## 7. Known limitations (be upfront at the viva)

* Single-instance service (SQLite, local files). Scale-out would need Postgres + object storage + a job queue.
* The real MiniLM retrieval thresholds are not calibrated on a labelled corpus (they could not be tuned in the build environment).
* Elasticity is *observational*: it measures association between price and quantity, not a controlled experiment.
* Forecasts are daily-revenue models; on noisy data they honestly report `unreliable`.
* Role detection is heuristic; low-confidence guesses are flagged, and the user can rename columns.
