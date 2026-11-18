from fastapi.testclient import TestClient

from app.llm.gateway import LLMGateway
from app.llm.schemas import ChatResult, Usage
from app.main import app
from app.routes.chat import get_gateway


def make_gateway_stream(events):
    async def fake_stream(messages, **extra):
        for ev in events:
            if isinstance(ev, Exception):
                raise ev
            yield ev

    gw = object.__new__(LLMGateway)  # 只借用类型，不真正初始化 client
    gw.stream = fake_stream
    return gw


def token(text):
    return {"type": "token", "text": text}


def done():
    r = ChatResult(
        content="ok",
        model="fake",
        usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        latency_ms=100,
        request_id="abc123",
        cost=0.0001,
        ttft_ms=50,
    )
    return {"type": "done", "result": r}


def test_sse_stream_ok():
    gw = make_gateway_stream([token("你"), token("好"), done()])
    app.dependency_overrides[get_gateway] = lambda: gw
    try:
        with TestClient(app) as client:
            with client.stream("POST", "/v1/chat/stream",
                               json={"messages": [{"role": "user", "content": "hi"}]}) as r:
                body = "".join(r.iter_text())
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert body.count("event: token") == 2
    assert body.count("event: done") == 1
    assert '"request_id": "abc123"' in body
    assert '"cost": 0.0001' in body


def test_sse_stream_error_hides_details():
    gw = make_gateway_stream([token("x"), RuntimeError("内部秘密，不得外泄")])
    app.dependency_overrides[get_gateway] = lambda: gw
    try:
        with TestClient(app) as client:
            with client.stream("POST", "/v1/chat/stream",
                               json={"messages": [{"role": "user", "content": "hi"}]}) as r:
                body = "".join(r.iter_text())
    finally:
        app.dependency_overrides.clear()
    assert "event: error" in body
    assert "内部秘密" not in body
    assert "LLM 调用失败" in body
