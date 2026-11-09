"""Hybrid retrieval: vector search (Qdrant ``query_points``) + lightweight BM25 re-rank.

Pipeline: embed the query -> search ``kb_shared``, the user's collection and the dataset collection ->
candidate pool -> BM25 over the pool -> combined = 0.6 * cosine + 0.4 * (bm25 / max bm25) ->
keep chunks with cosine >= MIN_COSINE and combined >= MIN_COMBINED -> top-k (default 4).
If nothing survives, the caller must say it could not find the answer (never guess).
These thresholds are tunable constants; they were set for MiniLM-style cosine scores.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from . import store
from .embeddings import get_embedder
from .store import Hit

TOP_K = 4
POOL = 12
MIN_COSINE = 0.20
MIN_COMBINED = 0.30
_STOP = set(
    "a an the of to in on for and or is are was were be been it its this that these those with as at by from "
    "what which who how do does did can could should would will my our your i we you they he she me us them "
    "about any there their if not no yes please tell show give".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 1]


def bm25_scores(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    toks = [tokenize(d) for d in docs]
    n = len(docs)
    if n == 0:
        return []
    avg = sum(len(t) for t in toks) / n or 1.0
    df = Counter(w for t in toks for w in set(t))
    out = []
    for t in toks:
        tf, score = Counter(t), 0.0
        for q in set(tokenize(query)):
            if q in tf:
                idf = math.log(1 + (n - df[q] + 0.5) / (df[q] + 0.5))
                score += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * len(t) / avg))
        out.append(score)
    return out


def retrieve(query: str, user_id: str, dataset_id: str | None = None, k: int = TOP_K, collections: list[str] | None = None) -> list[Hit]:
    """Return up to ``k`` relevant chunks, best first. Raises VectorStoreUnavailable if Qdrant is down."""
    vec = get_embedder().encode([query])[0]
    cols = collections or [store.SHARED, store.user_collection(user_id)] + ([store.data_collection(dataset_id)] if dataset_id else [])
    pool: list[Hit] = []
    for col in cols:
        pool.extend(store.search(col, vec, limit=POOL))
    if not pool:
        return []
    bm = bm25_scores(query, [h.text for h in pool])
    top = max(bm) or 0.0
    scored = []
    for h, s in zip(pool, bm):
        combined = 0.6 * h.score + 0.4 * (s / top if top > 0 else 0.0)
        if h.score >= MIN_COSINE and combined >= MIN_COMBINED:
            scored.append((combined, h))
    scored.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for combined, h in scored:  # de-duplicate identical text (e.g. same doc in two scopes)
        key = h.text[:120]
        if key in seen:
            continue
        seen.add(key)
        h.score = round(combined, 4)
        out.append(h)
        if len(out) == k:
            break
    return out
