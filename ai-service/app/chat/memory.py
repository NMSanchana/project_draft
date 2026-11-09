"""Conversation storage: ownership checks, message log and the last query plan (for follow-ups)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import ChatMessage, Conversation, ConversationState
from .plan import QueryPlan

HISTORY_TURNS = 6


def get_or_create(db: Session, user_id: str, dataset_id: str, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conv = db.get(Conversation, conversation_id)
        if conv is None:
            raise AppError(404, "Conversation not found.", "CONVERSATION_NOT_FOUND")
        if conv.user_id != user_id or conv.dataset_id != dataset_id:
            raise AppError(403, "You do not have access to this conversation.", "FORBIDDEN")
        return conv
    conv = Conversation(user_id=user_id, dataset_id=dataset_id)
    db.add(conv)
    db.commit()
    return conv


def add_message(
    db: Session, conv: Conversation, role: str, content: str, intent: str | None = None, sources: list[str] | None = None
) -> None:
    db.add(
        ChatMessage(
            conversation_id=conv.id,
            user_id=conv.user_id,
            dataset_id=conv.dataset_id,
            role=role,
            content=content,
            intent=intent,
            sources=sources,
        )
    )
    db.commit()


def recent(db: Session, conv: Conversation, n: int = HISTORY_TURNS) -> list[ChatMessage]:
    rows = db.query(ChatMessage).filter(ChatMessage.conversation_id == conv.id).order_by(ChatMessage.id.desc()).limit(n * 2).all()
    return list(reversed(rows))


def last_plan(db: Session, conv: Conversation) -> QueryPlan | None:
    st = db.get(ConversationState, conv.id)
    raw = (st.state or {}).get("last_plan") if st else None
    if not raw:
        return None
    try:
        return QueryPlan.model_validate(raw)
    except Exception:  # noqa: BLE001 - stale/incompatible state is simply ignored
        return None


def save_plan(db: Session, conv: Conversation, plan: QueryPlan) -> None:
    st = db.get(ConversationState, conv.id)
    data = {"last_plan": plan.model_dump(mode="json")}
    if st is None:
        db.add(ConversationState(conversation_id=conv.id, state=data))
    else:
        st.state = data
    db.commit()
