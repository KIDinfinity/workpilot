"""会话落库：保存一轮问答（user + assistant 两条消息）。"""

import json

from sqlmodel import Session

from app.db.models import Conversation, Message, utcnow


def save_turn(
    session: Session,
    conversation_id: str | None,
    question: str,
    answer: str,
    citations: list[dict],
    usage: dict | None,
) -> tuple[str, str]:
    conv = session.get(Conversation, conversation_id) if conversation_id else None
    if conv is None:
        conv = Conversation(title=question[:30])
        session.add(conv)
    conv.updated_at = utcnow()
    session.add(Message(conversation_id=conv.id, role="user", content=question))
    ans = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        citations_json=json.dumps(citations, ensure_ascii=False),
        usage_json=json.dumps(usage or {}, ensure_ascii=False),
    )
    session.add(ans)
    session.commit()
    return conv.id, ans.id
