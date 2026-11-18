"""会话 / 消息 / 反馈路由（Day24）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app.db.models import (
    Conversation,
    Feedback,
    FeedbackRating,
    FeedbackReason,
    Message,
)
from app.db.session import get_session

router = APIRouter(prefix="/v1", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class FeedbackIn(BaseModel):
    rating: FeedbackRating
    reason: FeedbackReason | None = None
    comment: str | None = Field(default=None, max_length=1000)


@router.get("/conversations", response_model=list[Conversation])
def list_conversations(
    s: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(le=200)] = 50,
) -> list[Conversation]:
    return s.exec(
        select(Conversation).order_by(col(Conversation.updated_at).desc()).limit(limit)
    ).all()


@router.post("/conversations", response_model=Conversation, status_code=201)
def create_conversation(
    body: ConversationCreate, s: Annotated[Session, Depends(get_session)]
) -> Conversation:
    conv = Conversation(title=body.title or "新会话")
    s.add(conv)
    s.commit()
    s.refresh(conv)
    return conv


@router.get("/conversations/{conv_id}/messages", response_model=list[Message])
def list_messages(conv_id: str, s: Annotated[Session, Depends(get_session)]) -> list[Message]:
    if not s.get(Conversation, conv_id):
        raise HTTPException(404, "conversation not found")
    return s.exec(
        select(Message).where(Message.conversation_id == conv_id).order_by(col(Message.created_at))
    ).all()


@router.post("/messages/{message_id}/feedback", response_model=Feedback, status_code=201)
def give_feedback(
    message_id: str, body: FeedbackIn, s: Annotated[Session, Depends(get_session)]
) -> Feedback:
    msg = s.get(Message, message_id)
    if msg is None or msg.role != "assistant":
        raise HTTPException(404, "assistant message not found")
    if body.rating == FeedbackRating.down and body.reason is None:
        raise HTTPException(422, "reason is required for down rating")
    fb = s.exec(select(Feedback).where(Feedback.message_id == message_id)).first() or Feedback(
        message_id=message_id, rating=body.rating
    )
    fb.rating, fb.reason, fb.comment = body.rating, body.reason, body.comment
    s.add(fb)
    s.commit()
    s.refresh(fb)
    return fb
