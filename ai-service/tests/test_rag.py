import sys
import types

import numpy as np
import pytest
from qdrant_client import QdrantClient

from app.db import init_db, init_engine, session_scope
from app.models import KBDocument
from app.rag import chunking, embeddings, facts, ingest, retriever, store
from app.rag.store import VectorStoreUnavailable
from tests.conftest import ROOT, SAMPLE_DIR
from tests.fakes import HashEmbedder

KB = ROOT / "ai-service" / "knowledge_base"


@pytest.fixture()
def rag(_env, monkeypatch):
    """Fake embedder + in-memory Qdrant + relaxed thresholds (the defaults are tuned for MiniLM cosine scores)."""
    init_engine()
    init_db()
    embeddings.set_embedder(HashEmbedder())
    store.set_client(QdrantClient(":memory:"))
    monkeypatch.setattr(retriever, "MIN_COSINE", 0.05)
    monkeypatch.setattr(retriever, "MIN_COMBINED", 0.15)
    db = session_scope()
    db.query(KBDocument).delete()
    db.commit()
    yield db
    db.close()
    embeddings.set_embedder(None)
    store.set_client(None)


def _count(col):
    c = store.get_client()
    return c.count(col, exact=True).count if c.collection_exists(col) else 0


# ------------------------------------------------------------------ chunking / extraction
def test_chunks_are_sentence_aware_sized_overlapping_and_keep_pages():
    para = " ".join(f"Sentence number {i} talks about returns, refunds and shipping rules for customers." for i in range(40))
    chunks = chunking.chunk_pages([(1, para), (2, "Short second page. It has two sentences.")])
    assert len(chunks) >= 4 and [c.chunk_id for c in chunks] == list(range(len(chunks)))
    for c in chunks[:-2]:
        assert 200 <= len(c.text) <= chunking.HARD_MAX and c.text.rstrip()[-1] in ".!?"  # ends at a sentence boundary
    p1 = [c for c in chunks if c.page == 1]
    assert all(a.text[-60:].split(".")[-2].strip() in b.text for a, b in zip(p1, p1[1:]))  # overlap carries the last sentence
    assert chunks[-1].page == 2 and chunks[-1].text.startswith("Short second page")  # never spans pages


def test_very_long_sentence_is_split_and_empty_input_yields_nothing():
    long = "word " * 600
    assert all(len(c.text) <= chunking.HARD_MAX for c in chunking.chunk_pages([(1, long)]))
    assert chunking.chunk_pages([(1, "   \n\n ")]) == []


def test_extract_pages_for_txt_md_pdf_and_failures():
    assert ingest.extract_pages("héllo world".encode(), "a.txt") == [(1, "héllo world")]
    assert ingest.extract_pages(b"# T\nbody", "a.md")[0][0] == 1
    pages = ingest.extract_pages((SAMPLE_DIR / "business_policy.pdf").read_bytes(), "business_policy.pdf")
    assert pages and "30 days" in pages[0][1]
    with pytest.raises(ingest.DocumentError, match="No text"):
        ingest.extract_pages(b"   ", "empty.txt")
    with pytest.raises(ingest.DocumentError, match="PDF could not be read"):
        ingest.extract_pages(b"not a pdf", "x.pdf")
    with pytest.raises(ingest.DocumentError, match="Only"):
        ingest.extract_pages(b"x", "x.docx")


def test_clean_name_sanitises_but_keeps_supported_extension():
    assert ingest.clean_name("../../My Policy (v2).PDF") == "My_Policy_v2.pdf"
    assert ingest.clean_name("notes.md") == "notes.md"


# ------------------------------------------------------------------ ingestion
def test_ingest_is_idempotent_and_delete_removes_vectors(rag):
    raw = (KB / "business_policy.md").read_bytes()
    a = ingest.ingest_bytes(rag, raw, "business_policy.md", user_id="alice")
    n = _count(store.user_collection("alice"))
    assert a["status"] == "ingested" and n == a["chunks"] > 0
    b = ingest.ingest_bytes(rag, raw, "renamed.md", user_id="alice")  # same content -> duplicate
    assert b["status"] == "duplicate" and b["id"] == a["id"] and _count(store.user_collection("alice")) == n
    ingest.delete_document(rag, rag.get(KBDocument, a["id"]))
    assert _count(store.user_collection("alice")) == 0 and rag.query(KBDocument).count() == 0


def test_user_isolation_and_shared_visibility(rag):
    ingest.ingest_bytes(
        rag, b"Alice private memo. The secret launch date is 14 July and the codename is Falcon.", "memo.txt", user_id="alice"
    )
    ingest.ingest_bytes(rag, (KB / "business_policy.md").read_bytes(), "business_policy.md", user_id=ingest.SHARED_USER, scope="shared")
    alice = retriever.retrieve("What is the secret launch date codename?", "alice")
    bob = retriever.retrieve("What is the secret launch date codename?", "bob")
    assert any("Falcon" in h.text for h in alice) and not any("Falcon" in h.text for h in bob)  # A's docs never reach B
    for u in ("alice", "bob"):  # shared KB reaches everyone
        assert any("30 days" in h.text for h in retriever.retrieve("How many days to return an item?", u))


def test_dataset_scoped_documents_live_in_the_dataset_collection(rag):
    ingest.ingest_bytes(rag, b"Supplier terms: payment within 45 days.", "terms.txt", user_id="alice", scope="dataset", dataset_id="ds1")
    assert _count(store.data_collection("ds1")) == 1 and _count(store.user_collection("alice")) == 0
    assert retriever.retrieve("payment days supplier", "alice", "ds1") and not retriever.retrieve("payment days supplier", "alice", "ds2")
    with pytest.raises(ingest.DocumentError, match="datasetId"):
        ingest.ingest_bytes(rag, b"x", "a.txt", user_id="alice", scope="dataset")


def test_kb_folder_sync_adds_updates_and_removes(rag, tmp_path):
    (tmp_path / "a.md").write_text("Alpha document. The alpha rule is 11 days.")
    (tmp_path / "b.txt").write_text("Beta document. The beta rule is 22 days.")
    (tmp_path / "ignore.csv").write_text("x,y")
    r = ingest.ingest_kb_folder(rag, tmp_path)
    assert sorted(r["ingested"]) == ["a.md", "b.txt"] and not r["errors"]
    assert ingest.ingest_kb_folder(rag, tmp_path)["duplicate"] == ["a.md", "b.txt"]  # idempotent
    (tmp_path / "a.md").write_text("Alpha document. The alpha rule is now 99 days.")  # edited file replaces old vectors
    r = ingest.ingest_kb_folder(rag, tmp_path)
    assert r["ingested"] == ["a.md"] and rag.query(KBDocument).filter_by(file_name="a.md").count() == 1
    hits = retriever.retrieve("alpha rule days", "x")
    assert any("99 days" in h.text for h in hits) and not any("11 days" in h.text for h in hits)
    (tmp_path / "b.txt").unlink()
    assert ingest.ingest_kb_folder(rag, tmp_path)["removed"] == ["b.txt"]
    assert not any("beta" in h.text.lower() for h in retriever.retrieve("beta rule days", "x"))
    (tmp_path / "bad.txt").write_text("   ")
    assert "bad.txt" in ingest.ingest_kb_folder(rag, tmp_path)["errors"][0]


def test_folder_signature_changes_when_files_change(tmp_path):
    (tmp_path / "a.md").write_text("one")
    s1 = ingest.folder_signature(tmp_path)
    (tmp_path / "a.md").write_text("two!")
    assert ingest.folder_signature(tmp_path) != s1 and ingest.folder_signature(tmp_path / "missing") == ()


# ------------------------------------------------------------------ retrieval quality (pipeline) + eval set
EVAL = [  # (question, expected file, text that the retrieved chunk must contain)
    ("How many days do customers have to return an item?", "business_policy.md", "30 days"),
    ("How long do refunds take to process?", "business_policy.md", "5-7 business days"),
    ("Is shipping free for large orders?", "business_policy.md", "$75"),
    ("What is the warranty period for electronics?", "business_policy.md", "12-month"),
    ("How much loyalty points do Gold customers earn?", "business_policy.md", "10%"),
    ("What is the maximum discount sales staff can give without approval?", "pricing_discount_guidelines.md", "10%"),
    ("Who must approve a discount above 20 percent?", "pricing_discount_guidelines.md", "director"),
    ("Can we price an item below cost?", "pricing_discount_guidelines.md", "8% margin floor"),
    ("How often can list prices change?", "pricing_discount_guidelines.md", "once per quarter"),
    ("What is the email response time?", "customer_service_playbook.md", "24 hours"),
    ("When are complaints escalated to a supervisor?", "customer_service_playbook.md", "48 hours"),
    ("What voucher is sent to inactive customers?", "customer_service_playbook.md", "10% voucher"),
]


def test_rag_evaluation_recall_at_4(rag):
    ingest.ingest_kb_folder(rag, KB)
    hit, rows = 0, []
    for q, file, needle in EVAL:
        top = retriever.retrieve(q, "anyone", k=4)
        ok = any(h.source == file and needle in h.text for h in top)
        hit += ok
        rows.append((ok, q))
    recall = hit / len(EVAL)
    print(f"\nRAG eval (fake embedder, pipeline only): recall@4 = {recall:.2f} ({hit}/{len(EVAL)})")
    assert len(EVAL) >= 10 and recall >= 0.8, [r for r in rows if not r[0]]


def test_irrelevant_question_returns_nothing(rag):
    ingest.ingest_kb_folder(rag, KB)
    assert retriever.retrieve("quantum chromodynamics banana smoothie recipe", "u") == []


def test_bm25_prefers_chunks_with_the_rare_keyword():
    docs = ["general policy about shipping and delivery", "the warranty claim process for electronics", "loyalty points and gold status"]
    s = retriever.bm25_scores("warranty electronics", docs)
    assert s[1] > 0 and s[0] == 0 and s[2] == 0 and retriever.bm25_scores("x", []) == []


# ------------------------------------------------------------------ graceful degradation + embedder wrapper
def test_vector_store_down_raises_a_clean_error(rag):
    store.set_client(QdrantClient(url="http://127.0.0.1:9", timeout=1))
    with pytest.raises(VectorStoreUnavailable):
        store.ping()
    with pytest.raises(VectorStoreUnavailable):
        retriever.retrieve("anything", "u")
    with pytest.raises(VectorStoreUnavailable):
        ingest.ingest_bytes(rag, b"Some text here for a document.", "a.txt", user_id="u")
    rag.rollback()


def test_minilm_wrapper_is_lazy_batches_and_returns_float32(monkeypatch):
    calls = {}

    class FakeST:
        def __init__(self, name):
            calls["name"] = name

        def encode(self, texts, **kw):
            calls["kw"] = kw
            return np.ones((len(texts), 384))

    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(SentenceTransformer=FakeST))
    embeddings.set_embedder(None)
    assert embeddings.is_loaded() is False
    v = embeddings.get_embedder().encode(["a", "b"])
    assert embeddings.is_loaded() and v.shape == (2, 384) and v.dtype == np.float32
    assert calls["name"] == "sentence-transformers/all-MiniLM-L6-v2" and calls["kw"]["normalize_embeddings"] is True
    assert embeddings.get_embedder() is embeddings.get_embedder()  # loaded once
    assert embeddings.get_embedder().encode([]).shape == (0, 384)
    embeddings.set_embedder(None)


# ------------------------------------------------------------------ dataset-fact index
def test_dataset_facts_are_indexed_and_retrievable(rag):
    from app.pipeline import stages
    from app.pipeline.assemble import run_fast_phase
    from app.pipeline.enrichment import EnrichmentContext

    fr = run_fast_phase((SAMPLE_DIR / "sample_ecommerce.csv").read_bytes(), "s.csv", "dsX")
    ctx = EnrichmentContext("dsX", "alice", fr.clean_df, fr.analytics)
    for _, fn in stages.DEFAULT_STAGES[:-2]:
        fn(ctx)
    docs = facts.build_fact_docs(fr.clean_df, ctx.analytics, ctx.modules)
    titles = [t for t, _ in docs]
    assert "Key metrics" in titles and "Revenue by region" in titles and any(t.startswith("Insight:") for t in titles)
    n = facts.index_dataset("dsX", fr.clean_df, ctx.analytics, ctx.modules)
    assert n == len(docs) == _count(store.data_collection("dsX"))
    top = retriever.retrieve("What is the revenue by region?", "alice", "dsX", k=2)
    assert top and top[0].source.startswith("dataset facts") and "West" in top[0].text
    facts.index_dataset("dsX", fr.clean_df, ctx.analytics, ctx.modules)  # re-index replaces, no duplicates
    assert _count(store.data_collection("dsX")) == n


def test_embedder_load_failure_becomes_a_clear_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)  # import raises ImportError
    embeddings.set_embedder(None)
    with pytest.raises(embeddings.EmbedderUnavailable, match="needs internet"):
        embeddings.get_embedder()
    assert embeddings.is_loaded() is False


def test_index_stage_is_skipped_not_failed_when_embedder_is_missing(rag, monkeypatch):
    from app.pipeline import stages
    from app.pipeline.assemble import run_fast_phase
    from app.pipeline.enrichment import EnrichmentContext

    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    embeddings.set_embedder(None)
    fr = run_fast_phase((SAMPLE_DIR / "sample_ecommerce.csv").read_bytes(), "s.csv", "dsE")
    ctx = EnrichmentContext("dsE", "alice", fr.clean_df, fr.analytics)
    stages.stage_index(ctx)
    assert ctx.modules["index"]["status"] == "skipped" and "embedding model" in ctx.modules["index"]["reason"]
