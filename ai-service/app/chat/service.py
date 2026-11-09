"""Chat orchestration: guard -> intent -> (planner+executor | ML answer | RAG) -> plain-text reply."""

from __future__ import annotations

import logging
from collections import OrderedDict

from sqlalchemy.orm import Session

from ..models import Dataset, DatasetResult
from ..security import CurrentUser
from ..storage import dataset_dir, load_clean_frame
from . import composer, docs, guard, memory, ml_answers
from .executor import run_plan
from .planner import ChatData, make_plan
from .router import SMALLTALK, route

log = logging.getLogger(__name__)
_CACHE: "OrderedDict[tuple, ChatData]" = OrderedDict()


def _chat_data(user_id: str, dataset_id: str) -> ChatData:
    path = dataset_dir(user_id, dataset_id) / "clean.parquet"
    key = (dataset_id, path.stat().st_mtime_ns if path.exists() else 0)
    if key not in _CACHE:
        _CACHE[key] = ChatData.build(load_clean_frame(user_id, dataset_id))
        while len(_CACHE) > 8:
            _CACHE.popitem(last=False)
    return _CACHE[key]


def handle_chat(db: Session, user: CurrentUser, ds: Dataset, message: str, conversation_id: str | None) -> dict:
    """Answer one message. Always returns ``{answer, intent, sources, conversationId[, result]}``."""
    conv = memory.get_or_create(db, user.id, ds.id, conversation_id)
    memory.add_message(db, conv, "user", message)
    intent = route(message)
    sources: list[str] = []
    result: dict | None = None
    try:
        if intent.name == "blocked":
            text = guard.REFUSAL
        elif intent.name == "smalltalk":
            text = SMALLTALK
        elif intent.name == "document_question":
            ans = docs.answer_documents(message, user.id, ds.id)
            text, sources = ans.text, ans.sources
        elif intent.name == "ml_insight":
            res = db.get(DatasetResult, ds.id)
            modules = dict(res.modules) if res else {}
            try:
                df = _chat_data(user.id, ds.id).df
            except FileNotFoundError:
                df = None
            text = ml_answers.answer_ml(intent.module, message, modules, df, ds.status)
            sources = [f"ml:{intent.module}"]
            if intent.module in ("segments", "churn") and modules.get("churn") is not None:
                sources = ["ml:segments", "ml:churn"] if intent.module == "segments" else ["ml:churn", "ml:segments"]
        else:  # data_query
            try:
                data = _chat_data(user.id, ds.id)
            except FileNotFoundError:
                text = "The cleaned data for this dataset is missing. Please upload the file again."
                data = None
            if data is not None:
                pr = make_plan(message, data, memory.last_plan(db, conv))
                if pr.plan is None:
                    text = pr.error or "I couldn't understand that question."
                else:
                    ex = run_plan(pr.plan, data.df)
                    text = composer.data_answer(ex)
                    if ex.ok:
                        memory.save_plan(db, conv, pr.plan)
                        sources = ["data"]
                        result = {
                            "metric": ex.plan.metric,
                            "operation": ex.plan.operation,
                            "value": ex.value,
                            "previous": ex.previous,
                            "rows": ex.rows,
                            "plan": ex.plan.model_dump(mode="json", exclude_none=True),
                        }
    except Exception:  # noqa: BLE001 - never leak a stack trace into the chat
        log.exception("Chat handler failed")
        text = "Sorry, something went wrong while answering that. Please try rephrasing the question."
        sources = []
    answer = composer.plain(text)
    memory.add_message(db, conv, "assistant", answer, intent.name, sources)
    out = {"answer": answer, "intent": intent.name, "sources": sources, "conversationId": conv.id}
    if result is not None:
        out["result"] = result
    return out
