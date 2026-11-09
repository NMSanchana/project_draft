"""Qdrant access: collections per user/dataset, idempotent upserts, search, deletion.

Collections: ``kb_shared`` (files in knowledge_base/), ``kb_<userId>`` (a user's uploads) and
``data_<datasetId>`` (a dataset's own facts + dataset-scoped uploads). Every failure raises
:class:`VectorStoreUnavailable` so callers can degrade gracefully.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from ..config import get_settings
from ..storage import safe_id
from .embeddings import DIM

log = logging.getLogger(__name__)
SHARED = "kb_shared"
_client: QdrantClient | None = None


class VectorStoreUnavailable(RuntimeError):
    """Qdrant is down or a call failed."""


@dataclass
class Hit:
    text: str
    source: str
    page: int
    chunk_id: int
    score: float
    collection: str
    doc_id: str


def user_collection(user_id: str) -> str:
    return f"kb_{safe_id(user_id)}"


def data_collection(dataset_id: str) -> str:
    return f"data_{safe_id(dataset_id)}"


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=get_settings().qdrant_url, timeout=5.0)
    return _client


def set_client(c: QdrantClient | None) -> None:
    """Inject a client (tests use ``QdrantClient(':memory:')``)."""
    global _client
    _client = c


def _wrap(fn):
    def inner(*a, **kw):
        try:
            return fn(*a, **kw)
        except VectorStoreUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - connection refused, timeouts, API errors
            raise VectorStoreUnavailable(f"Vector database unavailable: {str(exc)[:120]}") from exc

    inner.__name__ = fn.__name__
    return inner


@_wrap
def ping() -> bool:
    get_client().get_collections()
    return True


@_wrap
def ensure_collection(name: str) -> None:
    c = get_client()
    if not c.collection_exists(name):
        c.create_collection(name, vectors_config=qm.VectorParams(size=DIM, distance=qm.Distance.COSINE))


@_wrap
def upsert_chunks(collection: str, doc_id: str, source: str, chunks, vectors, extra: dict | None = None) -> int:
    ensure_collection(collection)
    points = [
        qm.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc_id}:{ch.chunk_id}")),
            vector=[float(x) for x in vec],
            payload={"doc_id": doc_id, "source": source, "page": ch.page, "chunk_id": ch.chunk_id, "text": ch.text, **(extra or {})},
        )
        for ch, vec in zip(chunks, vectors)
    ]
    for i in range(0, len(points), 128):
        get_client().upsert(collection, points=points[i : i + 128], wait=True)
    return len(points)


@_wrap
def delete_doc(collection: str, doc_id: str) -> None:
    c = get_client()
    if c.collection_exists(collection):
        c.delete(
            collection,
            points_selector=qm.FilterSelector(filter=qm.Filter(must=[qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id))])),
            wait=True,
        )


@_wrap
def delete_collection(name: str) -> None:
    c = get_client()
    if c.collection_exists(name):
        c.delete_collection(name)


@_wrap
def search(collection: str, vector, limit: int = 12, score_threshold: float | None = None) -> list[Hit]:
    c = get_client()
    if not c.collection_exists(collection):
        return []
    res = c.query_points(collection, query=[float(x) for x in vector], limit=limit, score_threshold=score_threshold, with_payload=True)
    return [
        Hit(
            text=p.payload["text"],
            source=p.payload["source"],
            page=int(p.payload.get("page", 1)),
            chunk_id=int(p.payload.get("chunk_id", 0)),
            score=float(p.score),
            collection=collection,
            doc_id=p.payload.get("doc_id", ""),
        )
        for p in res.points
    ]
