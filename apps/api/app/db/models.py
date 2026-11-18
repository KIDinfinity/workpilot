"""Day24 会话历史 + 反馈数据模型。

三张表：conversation（会话）/ message（消息）/ feedback（一条答案一个反馈，再评即更新）。
字段按 SQLModel 约定用 `table=True` 声明；JSON 列存字符串，保持只读快照、不参与查询。
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class Conversation(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str = Field(default="新会话", max_length=200)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, index=True)


class Message(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    conversation_id: str = Field(foreign_key="conversation.id", index=True)
    role: str = Field(max_length=16)  # user / assistant
    content: str
    citations_json: str | None = None  # json.dumps(list[Citation])
    usage_json: str | None = None  # tokens / cost / latency（W3 计量结果）
    created_at: datetime = Field(default_factory=utcnow)


class FeedbackRating(StrEnum):
    up = "up"
    down = "down"


class FeedbackReason(StrEnum):
    wrong = "wrong"  # 答案事实错误
    no_citation = "no_citation"  # 没有引用 / 引用对不上
    irrelevant = "irrelevant"  # 答非所问 / 检索跑偏
    incomplete = "incomplete"  # 不完整
    other = "other"


class Feedback(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # 一条消息一个反馈，再评即更新
    message_id: str = Field(foreign_key="message.id", unique=True, index=True)
    rating: FeedbackRating
    reason: FeedbackReason | None = None
    comment: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utcnow)


class KBDocument(SQLModel, table=True):
    """知识库文档（Day25）：上传 → 后台解析入库的元数据与状态机。"""

    __tablename__ = "kb_document"
    id: str = Field(default_factory=new_id, primary_key=True)
    filename: str = Field(max_length=200)
    object_key: str | None = None  # MinIO 中的 key
    size: int = 0
    status: str = Field(default="pending", index=True)  # pending / processing / ready / failed
    error: str | None = Field(default=None, max_length=500)
    chunks: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
