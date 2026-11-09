"""Document ingestion: extract -> chunk -> embed -> Qdrant, idempotent by content hash.

Scopes: ``shared`` (files in knowledge_base/, visible to every user), ``user`` (that user only) and
``dataset`` (tied to one dataset; removed with it). Run ``python -m app.rag.ingest`` to (re)ingest
knowledge_base/ manually.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from pathlib import Path, PurePath

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import KBDocument
from . import store
from .chunking import chunk_pages
from .embeddings import get_embedder

log = logging.getLogger(__name__)
ALLOWED = {".pdf", ".txt", ".md"}
SHARED_USER = "__shared__"


class DocumentError(ValueError):
    """The document cannot be used (message is shown to the user, HTTP 422)."""


def clean_name(name: str | None) -> str:
    """Strip any path, keep ``[A-Za-z0-9._-]`` and preserve a supported extension (.pdf/.txt/.md)."""
    base = PurePath((name or "document.txt").replace("\\", "/")).name
    ext = PurePath(base).suffix.lower()
    stem = base[: -len(ext)] if ext else base
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "document"
    return f"{stem[:100]}{ext if ext in ALLOWED else ''}"


def extract_pages(raw: bytes, filename: str) -> list[tuple[int, str]]:
    """Return ``[(page, text)]``. PDF pages come from pypdf; txt/md are one page."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            pages = [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
        except Exception as exc:  # noqa: BLE001
            raise DocumentError(f"The PDF could not be read ({str(exc)[:80]}).") from exc
    elif ext in (".txt", ".md"):
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        pages = [(1, text)]
    else:
        raise DocumentError("Only .pdf, .txt and .md documents are supported.")
    pages = [(n, re.sub(r"\s+\n", "\n", t)) for n, t in pages if t and t.strip()]
    if not pages:
        raise DocumentError("No text could be extracted (is this a scanned PDF? Scanned images are not supported).")
    return pages


def _target(scope: str, user_id: str, dataset_id: str | None) -> tuple[str, str]:
    if scope == "shared":
        return store.SHARED, SHARED_USER
    if scope == "dataset":
        if not dataset_id:
            raise DocumentError("scope=dataset needs a datasetId.")
        return store.data_collection(dataset_id), user_id
    return store.user_collection(user_id), user_id


def ingest_bytes(db: Session, raw: bytes, filename: str, *, user_id: str, scope: str = "user", dataset_id: str | None = None) -> dict:
    """Ingest one document. Returns ``{id, fileName, chunks, status}`` (status ``ingested`` or ``duplicate``)."""
    name = clean_name(filename)
    collection, owner = _target(scope, user_id, dataset_id)
    digest = hashlib.sha256(raw).hexdigest()
    q = db.query(KBDocument).filter(
        KBDocument.user_id == owner, KBDocument.scope == scope, KBDocument.dataset_id == (dataset_id if scope == "dataset" else None)
    )
    existing = q.filter(KBDocument.content_hash == digest).first()
    if existing:
        return {"id": existing.id, "fileName": existing.file_name, "chunks": existing.chunks, "status": "duplicate"}

    chunks = chunk_pages(extract_pages(raw, name))
    if not chunks:
        raise DocumentError("The document produced no usable text.")
    vectors = get_embedder().encode([c.text for c in chunks])
    if scope == "shared":  # an edited file replaces its older version
        for old in q.filter(KBDocument.file_name == name).all():
            store.delete_doc(collection, old.id)
            db.delete(old)
    doc = KBDocument(
        user_id=owner,
        scope=scope,
        dataset_id=dataset_id if scope == "dataset" else None,
        file_name=name,
        content_hash=digest,
        chunks=len(chunks),
    )
    db.add(doc)
    db.flush()
    store.upsert_chunks(collection, doc.id, name, chunks, vectors, {"scope": scope})  # raises if Qdrant is down
    db.commit()
    return {"id": doc.id, "fileName": name, "chunks": len(chunks), "status": "ingested"}


def delete_document(db: Session, doc: KBDocument) -> None:
    """Remove a document's vectors and its row."""
    collection = (
        store.SHARED
        if doc.scope == "shared"
        else store.data_collection(doc.dataset_id)
        if doc.scope == "dataset"
        else store.user_collection(doc.user_id)
    )
    store.delete_doc(collection, doc.id)
    db.delete(doc)
    db.commit()


def folder_signature(folder: Path | None = None) -> tuple:
    folder = folder or get_settings().kb_path
    if not folder.exists():
        return ()
    return tuple(
        sorted(
            (str(p.relative_to(folder)), p.stat().st_mtime_ns, p.stat().st_size)
            for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in ALLOWED
        )
    )


def ingest_kb_folder(db: Session, folder: Path | None = None) -> dict:
    """Sync ``knowledge_base/`` into ``kb_shared``: add/update new files, drop vectors of deleted ones."""
    folder = folder or get_settings().kb_path
    folder.mkdir(parents=True, exist_ok=True)
    out = {"ingested": [], "duplicate": [], "removed": [], "errors": []}
    present = set()
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in ALLOWED:
            continue
        present.add(clean_name(p.name))
        try:
            r = ingest_bytes(db, p.read_bytes(), p.name, user_id=SHARED_USER, scope="shared")
            out[r["status"]].append(r["fileName"])
        except DocumentError as exc:
            out["errors"].append(f"{p.name}: {exc}")
    for doc in db.query(KBDocument).filter(KBDocument.scope == "shared").all():
        if doc.file_name not in present:
            delete_document(db, doc)
            out["removed"].append(doc.file_name)
    return out


def main() -> None:  # pragma: no cover - manual CLI
    from ..db import init_db, session_scope

    logging.basicConfig(level="INFO")
    init_db()
    db = session_scope()
    try:
        res = ingest_kb_folder(db)
    finally:
        db.close()
    print(f"ingested={res['ingested']} unchanged={res['duplicate']} removed={res['removed']} errors={res['errors']}")


if __name__ == "__main__":  # pragma: no cover
    main()
