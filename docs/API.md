# AI service API

Base URL `http://localhost:8000` (interactive docs: `/docs`). Every route except `/health` needs `Authorization: Bearer <JWT>`; the token
is the one Nest returns from login/register (HS256, shared `JWT_SECRET`, must carry `exp`, `email` and `id` or `sub`).

```bash
# get a token from Nest (or copy the `token` cookie from your browser)
TOKEN=$(curl -s localhost:5000/api/auth/login -H 'Content-Type: application/json' \
        -d '{"email":"you@example.com","password":"..."}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
H="Authorization: Bearer $TOKEN"
```

## Errors
Always JSON: `{"success": false, "message": "<human readable>", "code": "<CODE>"}`.

| HTTP | code | When |
|---|---|---|
| 401 | `NOT_AUTHENTICATED`, `INVALID_TOKEN`, `TOKEN_EXPIRED` | missing/bad/expired token, missing identity claims |
| 403 | `FORBIDDEN` | someone else's dataset, conversation or document; deleting a shared KB file |
| 404 | `DATASET_NOT_FOUND`, `CONVERSATION_NOT_FOUND`, `DOCUMENT_NOT_FOUND`, `UNKNOWN_MODULE`, `NOT_FOUND` | unknown id / module |
| 409 | `NOT_READY`, `PRICING_NOT_READY` | report/simulation requested while analysis is still running |
| 413 | `FILE_TOO_LARGE` | file over `MAX_UPLOAD_MB` (10) |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | CSV endpoint: not `.csv`; document endpoint: not `.pdf/.txt/.md` |
| 422 | `INVALID_DATA` | CSV unusable (e.g. "No date column found...", empty, one column) |
| 422 | `VALIDATION_ERROR` | bad request body (e.g. `priceChangePct` outside ±20, message > 1000 chars) |
| 422 | `UNKNOWN_SEGMENT`, `OUT_OF_BOUNDS`, `PRICING_UNAVAILABLE`, `INVALID_DOCUMENT` | simulator / document problems |
| 500 | `INTERNAL_ERROR`, `SERVER_MISCONFIGURED` | bug / empty `JWT_SECRET` |
| 503 | `VECTOR_DB_DOWN`, `EMBEDDER_UNAVAILABLE` | Qdrant not running / embedding model not loadable |

## Health
`GET /health` (no auth) → `{"status":"ok","db":"up","qdrant":"up|down","ollama":"up|down|model_missing","model":"llama3.2:3b","embedder_loaded":false,"jwt_configured":true}`. Never fails because Ollama or Qdrant is down.

## Datasets
| Method & path | Purpose |
|---|---|
| `POST /ai/v1/datasets/analyze` | multipart `file` (CSV ≤ 10 MB), optional `business_name`. **Fast phase**: returns the full `ProcessedAnalytics` (+ `datasetId`, `status:"enriching"`, `quality`, `kpis`) and starts background enrichment |
| `GET /ai/v1/datasets/{id}` | latest result; `status` = `enriching` \| `ready` \| `failed` (+ `stage` while running). Insights grow as stages finish; `ml` holds compact module summaries |
| `GET /ai/v1/datasets` | your datasets |
| `DELETE /ai/v1/datasets/{id}` | deletes result, files, chat history, dataset documents **and** the Qdrant collection (`vectorsRemoved` tells if Qdrant was reachable) |
| `GET /ai/v1/datasets/{id}/ml/{module}` | full JSON; module ∈ `segments, churn, drivers, pricing, basket, forecast, anomalies`; `status` may be `pending` while enriching |
| `GET /ai/v1/datasets/{id}/report.pdf` | the PDF report (409 while enriching) |

```bash
curl -s -X POST localhost:8000/ai/v1/datasets/analyze -H "$H" -F file=@sample-data/retail_with_orders.csv
curl -s localhost:8000/ai/v1/datasets/$DS -H "$H"
curl -s localhost:8000/ai/v1/datasets/$DS/ml/forecast -H "$H"
curl -s localhost:8000/ai/v1/datasets/$DS/report.pdf -H "$H" -o report.pdf
```
`ProcessedAnalytics` fields are exactly those in `frontend/src/lib/analytics.ts`; extras are optional.

## Pricing simulator
`POST /ai/v1/pricing/simulate` `{"datasetId": "...", "segmentValue": "Groceries", "priceChangePct": 5}` (segment name or `All`; ±20 only).
```json
{"segment":"Groceries","price_change_pct":5,"reliable":true,"elasticity":-1.9,"elasticity_ci":[-2.1,-1.7],
 "units_change_pct":-8.9,"revenue_delta":-7500.0,"revenue_delta_range":[-9100.0,-6000.0],
 "profit_delta":-2100.0,"profit_delta_range":[-2600.0,-1700.0],"recommended":{"price_change_pct":-20.0,"optimises":"profit","expected_gain":9300.0}}
```
(Values above are illustrative.) An unreliable segment returns `{"reliable": false, "status": "unreliable", "message": "Insufficient evidence ..."}` and **no numbers**.

## Chat
`POST /ai/v1/chat` `{"datasetId": "...", "message": "revenue by region in March", "conversationId": "optional"}` →
```json
{"answer":"Revenue by region in March 2024 (top 4):\n1. West: $...","intent":"data_query","sources":["data"],
 "conversationId":"...","result":{"metric":"revenue","operation":"group","rows":[{"label":"West","value":123.45}],"plan":{...}}}
```
`intent` ∈ `data_query, ml_insight, document_question, smalltalk, blocked`. `sources` ∈ `data`, `ml:<module>`, `doc:<file>#p<page>`,
`data:<fact title>`. `answer` is plain text (≤ ~6 lines). `result` (data queries only) carries the exact numbers and the validated plan.
`GET /ai/v1/chat/history?datasetId=...` returns your messages for that dataset.

## Documents (RAG)
| Method & path | Purpose |
|---|---|
| `POST /ai/v1/rag/documents` | multipart `file` (.pdf/.txt/.md), `scope=user` (private, default) or `scope=dataset` + `datasetId`. Returns `{id, fileName, chunks, status: "ingested"\|"duplicate"}` |
| `GET /ai/v1/rag/documents` | your documents + shared `knowledge_base/` files (`shared: true`) |
| `DELETE /ai/v1/rag/documents/{id}` | remove your document and its vectors (shared files: delete them from the folder) |

```bash
curl -s -X POST localhost:8000/ai/v1/rag/documents -H "$H" -F file=@sample-data/supplier_terms.pdf -F scope=user
curl -s -X POST localhost:8000/ai/v1/chat -H "$H" -H 'Content-Type: application/json' \
     -d "{\"datasetId\":\"$DS\",\"message\":\"What are the supplier payment terms?\"}"
```
Files placed in `ai-service/knowledge_base/` are ingested automatically (every ~15 s) or with `./scripts/ingest_docs.sh`.
