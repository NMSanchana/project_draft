"""Chat endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..chat.service import handle_chat
from ..db import get_db
from ..models import ChatMessage
from ..security import CurrentUser, get_current_user
from .datasets import get_owned_dataset

router = APIRouter(prefix="/ai/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    datasetId: str
    message: str = Field(min_length=1, max_length=1000)
    conversationId: str | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    sources: list[str]
    conversationId: str
    result: dict | None = None


@router.post("", response_model=ChatResponse, response_model_exclude_none=True)
def chat(req: ChatRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Answer a question about the dataset (exact numbers), its ML insights, or uploaded documents."""
    ds = get_owned_dataset(db, req.datasetId, user)
    return handle_chat(db, user, ds, req.message.strip(), req.conversationId)


@router.get("/history")
def history(datasetId: str = Query(...), user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ds = get_owned_dataset(db, datasetId, user)
    rows = (
        db.query(ChatMessage).filter(ChatMessage.dataset_id == ds.id, ChatMessage.user_id == user.id).order_by(ChatMessage.id.asc()).all()
    )
    return [
        {
            "conversationId": m.conversation_id,
            "role": m.role,
            "content": m.content,
            "intent": m.intent,
            "sources": m.sources or [],
            "createdAt": m.created_at.isoformat(),
        }
        for m in rows
    ]
