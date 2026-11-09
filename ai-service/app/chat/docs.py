"""Document / dataset-fact question answering (RAG) with citations and an honest "not found"."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..llm import ollama_client
from ..llm.ollama_client import LLMUnavailable
from ..pipeline.narrative import _BAD_OUTPUT, allowed_numbers, is_grounded
from ..rag import retriever
from ..rag.embeddings import EmbedderUnavailable
from ..rag.store import Hit, VectorStoreUnavailable
from . import guard

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parent.parent / "llm" / "prompts"
NOT_FOUND = "I couldn't find that in your documents or your dataset facts."
NOTE_NO_LLM = "(AI phrasing is unavailable, so these are the most relevant passages.)"


@dataclass
class DocAnswer:
    text: str
    sources: list[str] = field(default_factory=list)
    llm_used: bool = False
    found: bool = True


def _is_fact(h: Hit) -> bool:
    return h.source.startswith("dataset facts")


def _label(h: Hit) -> str:
    return h.source.replace("dataset facts: ", "") if _is_fact(h) else f"{h.source} p.{h.page}"


def _best_sentences(text: str, question: str, n: int = 2, limit: int = 280) -> str:
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]
    q = set(retriever.tokenize(question))
    ranked = sorted(range(len(sents)), key=lambda i: (-len(q & set(retriever.tokenize(sents[i]))), i))
    keep = sorted(ranked[:n])
    out = " ".join(sents[i] for i in keep)
    return out if len(out) <= limit else out[: limit - 1].rstrip() + "…"


_GENERIC = {
    "according",
    "uploaded",
    "files",
    "file",
    "document",
    "documents",
    "policy",
    "policies",
    "say",
    "says",
    "tell",
    "explain",
    "dataset",
    "summary",
    "data",
    "many",
    "much",
    "have",
    "has",
    "our",
    "mine",
    "please",
}


def _stem(w: str) -> str:
    return w[:-1] if w.endswith("s") and len(w) > 3 else w


def _lexically_supported(question: str, hit: Hit) -> bool:
    """Without an LLM to judge answerability, require at least one content word of the question in the passage."""
    q = {_stem(t) for t in retriever.tokenize(question) if t not in _GENERIC}
    if not q:
        return True
    return bool(q & {_stem(t) for t in retriever.tokenize(hit.text + " " + hit.source)})


def _extractive(question: str, docs: list[Hit], facts: list[Hit]) -> str:
    lines = []
    if docs:
        lines.append(f"From your documents: {_best_sentences(docs[0].text, question)} (source: {_label(docs[0])})")
    if facts:
        lines.append(f"From your data: {_best_sentences(facts[0].text, question, n=2, limit=240)} (source: {_label(facts[0])})")
    return "\n".join(lines)


def _llm_answer(question: str, hits: list[Hit]) -> str | None:
    """Return a grounded LLM answer, ``""`` for NOT_FOUND, or None when the LLM is unavailable/untrustworthy."""
    try:
        if not ollama_client.is_available():
            return None
        excerpts = "\n".join(f"[{i}] ({_label(h)}) {guard.sanitize_context(h.text)}" for i, h in enumerate(hits, 1))
        system = (PROMPTS / "docs_system.txt").read_text()
        user = (PROMPTS / "docs_user.txt").read_text().replace("{excerpts}", excerpts).replace("{question}", question[:500])
        out = ollama_client.generate(system, user, temperature=0.2, timeout=45, retries=0).strip()
    except LLMUnavailable:
        return None
    if "NOT_FOUND" in out:
        return ""
    if _BAD_OUTPUT.search(out) or not is_grounded(out, allowed_numbers({"x": excerpts})):
        log.info("Discarding ungrounded LLM document answer")
        return None
    return out


def answer_documents(question: str, user_id: str, dataset_id: str | None) -> DocAnswer:
    try:
        hits = retriever.retrieve(question, user_id, dataset_id)
    except VectorStoreUnavailable:
        return DocAnswer(
            "Document search is unavailable right now (the vector database isn't running). " "Questions about your sales data still work.",
            found=False,
        )
    except EmbedderUnavailable as exc:
        log.warning("Embedding model unavailable: %s", exc)
        return DocAnswer(
            "Document search is unavailable right now (the embedding model could not be loaded). "
            "Questions about your sales data still work.",
            found=False,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Retrieval failed: %s", exc)
        return DocAnswer("Document search failed unexpectedly. Questions about your sales data still work.", found=False)
    if not hits:
        return DocAnswer(NOT_FOUND, found=False)

    docs = [h for h in hits if not _is_fact(h)]
    facts = [h for h in hits if _is_fact(h)]
    sources = [f"doc:{h.source}#p{h.page}" for h in docs[:3]] + [f"data:{_label(h)}" for h in facts[:2]]
    sources = list(dict.fromkeys(sources))
    ans = _llm_answer(question, docs + facts)
    if ans == "":
        return DocAnswer(NOT_FOUND, found=False)
    if ans is not None:
        head = "From your documents and data:" if docs and facts else ("From your documents:" if docs else "From your data:")
        cites = "; ".join(dict.fromkeys(_label(h) for h in (docs + facts)[:3]))
        return DocAnswer(f"{head} {ans}\nSources: {cites}", sources, llm_used=True)
    docs = [h for h in docs if _lexically_supported(question, h)]
    facts = [h for h in facts if _lexically_supported(question, h)]
    if not docs and not facts:
        return DocAnswer(NOT_FOUND, found=False)
    return DocAnswer(_extractive(question, docs, facts) + "\n" + NOTE_NO_LLM, sources, llm_used=False)
