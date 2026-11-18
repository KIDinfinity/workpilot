"""conversations 路由测试：用内存 SQLite（StaticPool）覆盖 get_session，不触真实库/LLM。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import Conversation, Feedback, Message
from app.db.session import get_session
from app.main import app

# 每个测试进程一个内存库；create_all 只建不存在的表
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SQLModel.metadata.create_all(engine)


def _override_session():
    with Session(engine) as s:
        yield s


@pytest.fixture(autouse=True)
def _use_memory_db():
    # 逐测试设置，避免被其他测试文件的 dependency_overrides.clear() 清掉
    app.dependency_overrides[get_session] = _override_session
    yield
    app.dependency_overrides.pop(get_session, None)


def _seed_assistant_message() -> tuple[str, str]:
    with Session(engine) as s:
        conv = Conversation(title="测试会话")
        s.add(conv)
        s.commit()
        msg = Message(conversation_id=conv.id, role="assistant", content="测试答案")
        s.add(msg)
        s.commit()
        return conv.id, msg.id


def test_feedback_down_requires_reason():
    _, mid = _seed_assistant_message()
    with TestClient(app) as client:  # 触 lifespan 只初始化真实库；路由走 override 的内存库
        r = client.post(f"/v1/messages/{mid}/feedback", json={"rating": "down"})
    assert r.status_code == 422
    assert "reason" in r.json()["error"]["message"]


def test_feedback_re_rate_updates_not_inserts():
    _, mid = _seed_assistant_message()
    with TestClient(app) as client:
        r1 = client.post(f"/v1/messages/{mid}/feedback", json={"rating": "up"})
        assert r1.status_code == 201
        first_id = r1.json()["id"]

        r2 = client.post(
            f"/v1/messages/{mid}/feedback",
            json={"rating": "down", "reason": "wrong", "comment": "事实错误"},
        )
        assert r2.status_code == 201
        assert r2.json()["id"] == first_id  # 再评是更新，不新增

    with Session(engine) as s:
        rows = s.exec(select(Feedback).where(Feedback.message_id == mid)).all()
        assert len(rows) == 1
        assert rows[0].rating.value == "down"
        assert rows[0].reason.value == "wrong"


def test_list_and_create_conversation():
    with TestClient(app) as client:
        created = client.post("/v1/conversations", json={"title": "新会话A"})
        assert created.status_code == 201
        conv_id = created.json()["id"]

        listed = client.get("/v1/conversations")
        assert listed.status_code == 200
        ids = [c["id"] for c in listed.json()]
        assert conv_id in ids


def test_list_messages_404_when_conv_missing():
    with TestClient(app) as client:
        r = client.get("/v1/conversations/does-not-exist/messages")
    assert r.status_code == 404
