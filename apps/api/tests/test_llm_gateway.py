import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APITimeoutError, AuthenticationError

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.llm.gateway import LLMGateway
from app.main import app
from app.routes.chat import get_gateway

FAKE_KEY = "sk-test-should-never-leak"
REQ = httpx.Request("POST", "https://llm.invalid/chat/completions")
MSGS = [{"role": "user", "content": "ping"}]


def ok_resp(text="pong"):
    return SimpleNamespace(
        model="fake-model",
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=1, total_tokens=6),
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
    )


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), 0

    async def create(self, **kwargs):
        self.calls += 1
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def make_gateway(outcomes):
    fake = FakeCompletions(outcomes)
    client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    settings = Settings(_env_file=None, llm_provider="deepseek", deepseek_api_key=FAKE_KEY)
    return LLMGateway(settings, client=client, backoff_s=0), fake


def test_success_returns_usage():
    gw, fake = make_gateway([ok_resp()])
    r = asyncio.run(gw.chat(MSGS))
    assert (r.content, r.usage.prompt_tokens, r.usage.total_tokens, fake.calls) == ("pong", 5, 6, 1)


def test_retry_then_success():
    gw, fake = make_gateway([APITimeoutError(request=REQ), APITimeoutError(request=REQ), ok_resp()])
    assert asyncio.run(gw.chat(MSGS)).content == "pong" and fake.calls == 3


def test_auth_error_not_retried():
    err = AuthenticationError("bad key", response=httpx.Response(401, request=REQ), body=None)
    gw, fake = make_gateway([err])
    with pytest.raises(AppError) as ei:
        asyncio.run(gw.chat(MSGS))
    assert ei.value.code == "llm_auth_failed" and fake.calls == 1


def test_timeout_exhausted_returns_504_without_key():
    gw, fake = make_gateway([APITimeoutError(request=REQ)] * 3)
    app.dependency_overrides[get_gateway] = lambda: gw
    try:
        r = TestClient(app).post("/v1/chat", json={"messages": MSGS})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 504 and r.json()["error"]["code"] == "llm_timeout"
    assert FAKE_KEY not in r.text and fake.calls == 3


@pytest.mark.live
def test_live_provider_smoke():
    s = get_settings()
    if not s.llm_api_key.get_secret_value():
        pytest.skip("LLM_API_KEY 未配置")
    r = asyncio.run(LLMGateway(s).chat([{"role": "user", "content": "只回复 pong"}], max_tokens=5))
    assert r.content and r.usage.prompt_tokens > 0
