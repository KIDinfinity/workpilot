"""文档助手 v0 路由测试：注入 FakeGW，不触真实 LLM（默认 -m 'not live' 即可跑）。"""

import json

from fastapi.testclient import TestClient

from app.llm.gateway import LLMGateway
from app.llm.schemas import ChatResult, Usage
from app.main import app
from app.routes.ask import get_gateway

VALID = json.dumps(
    {
        "answer": "结论：只有 VITE_ 前缀会暴露给客户端。",
        "key_points": ["import.meta.env 在构建时静态替换", "非 VITE_ 前缀不会进 bundle"],
        "confidence": "high",
        "needs_more_context": False,
    },
    ensure_ascii=False,
)


class FakeGW:
    """按顺序吐出预设回复（供 generate_structured 校验）。"""

    def __init__(self, outputs):
        self.outputs = list(outputs)

    async def chat(self, messages, **kw):
        return ChatResult(
            content=self.outputs.pop(0),
            model="fake",
            usage=Usage(prompt_tokens=12, completion_tokens=8, total_tokens=20),
            latency_ms=42,
            request_id="req-1",
            cost=0.000123,
        )


def _override(gw):
    app.dependency_overrides[get_gateway] = lambda: gw


def test_ask_returns_envelope():
    _override(FakeGW([VALID]))
    try:
        with TestClient(app) as client:
            r = client.post("/v1/ask", json={"question": "Vite 里哪些环境变量会暴露给客户端？"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]["confidence"] == "high"
    assert body["source_note"].startswith("来源：模型通用知识")
    assert body["prompt"] == "qa_answer.v0"
    assert body["usage"]["total_tokens"] == 20
    assert body["cost"] == 0.000123
    assert body["latency_ms"] == 42
    assert body["request_id"] == "req-1"


def test_ask_structured_failure_maps_to_502():
    # 两次非法 JSON → StructuredError → AppError（502，不外泄模型原文）
    _override(FakeGW(["这段不是 json", "这段也不是 json"]))
    try:
        with TestClient(app) as client:
            r = client.post("/v1/ask", json={"question": "任意研发问题"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "structured_output_failed"


def test_ask_rejects_too_short_question():
    with TestClient(app) as client:
        r = client.post("/v1/ask", json={"question": "x"})
    assert r.status_code == 422


def _stream_gateway(events):
    async def fake_stream(messages, **extra):
        for ev in events:
            yield ev

    gw = object.__new__(LLMGateway)  # 只借用类型，不初始化 client
    gw.stream = fake_stream
    return gw


def _done():
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


def test_ask_stream_done_carries_source_note():
    events = [{"type": "token", "text": "你"}, {"type": "token", "text": "好"}, _done()]
    gw = _stream_gateway(events)
    _override(gw)
    try:
        with TestClient(app) as client:
            with client.stream("POST", "/v1/ask/stream", json={"question": "解释一下 RAG"}) as r:
                body = "".join(r.iter_text())
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert body.count("event: token") == 2
    assert body.count("event: done") == 1
    assert "来源：模型通用知识" in body
    assert '"ttft_ms": 50' in body


def test_ask_stream_error_hides_details():
    gw = _stream_gateway([{"type": "token", "text": "x"}, RuntimeError("内部秘密，不得外泄")])
    _override(gw)
    try:
        with TestClient(app) as client:
            with client.stream("POST", "/v1/ask/stream", json={"question": "解释一下 RAG"}) as r:
                body = "".join(r.iter_text())
    finally:
        app.dependency_overrides.clear()
    assert "event: error" in body
    assert "内部秘密" not in body
