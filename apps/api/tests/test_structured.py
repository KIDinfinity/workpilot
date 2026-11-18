import json

import pytest

from app.llm import structured
from app.llm.schemas import ChatResult, StructuredAnswer, TaskBreakdown, TaskItem, Usage

GOOD = {
    "answer": "x",
    "key_points": [],
    "confidence": "low",
    "needs_more_context": True,
}
VALID = json.dumps(GOOD, ensure_ascii=False)
MISSING_FIELDS = '{"answer": "x"}'  # 缺 confidence / needs_more_context
NOT_JSON = "这是一段散文，不是 json"


class FakeGW:
    """按顺序吐出预设回复；记录每次收到的 messages 与 kwargs。"""

    def __init__(self, outputs):
        self.outputs, self.calls, self.kwargs = list(outputs), [], []

    async def chat(self, msgs, **kw):
        self.calls.append([dict(m) for m in msgs])
        self.kwargs.append(kw)
        return ChatResult(content=self.outputs.pop(0), model="fake", usage=Usage(), latency_ms=1)


async def test_first_try_ok_no_retry():
    fake = FakeGW([VALID])
    data, res = await structured.generate_structured(
        StructuredAnswer, [{"role": "user", "content": "q"}], gw=fake
    )
    assert data.confidence == "low" and res.model == "fake"
    assert len(fake.calls) == 1


async def test_retry_then_ok():
    fake = FakeGW([MISSING_FIELDS, VALID])
    data, _ = await structured.generate_structured(
        StructuredAnswer, [{"role": "user", "content": "q"}], gw=fake
    )
    assert data.confidence == "low" and len(fake.calls) == 2
    # 第二次请求把「模型原文 + 具体错误」带上了
    repair = fake.calls[1][-1]["content"]
    assert "未通过校验" in repair and "confidence" in repair
    assert fake.calls[1][-2]["content"] == MISSING_FIELDS  # 原样回放的 assistant 消息


async def test_two_bad_outputs_raise_structured_error():
    fake = FakeGW([NOT_JSON, NOT_JSON])
    with pytest.raises(structured.StructuredError, match="StructuredAnswer 校验失败"):
        await structured.generate_structured(
            StructuredAnswer, [{"role": "user", "content": "q"}], gw=fake
        )
    assert len(fake.calls) == 2  # max_retries=1 → 最多 2 次调用，不无限重试


async def test_extra_retries_are_configurable():
    fake = FakeGW([NOT_JSON, NOT_JSON, VALID])
    data, _ = await structured.generate_structured(
        StructuredAnswer, [{"role": "user", "content": "q"}], gw=fake, max_retries=2
    )
    assert data.needs_more_context is True and len(fake.calls) == 3


async def test_system_prompt_carries_schema_and_json_word():
    fake = FakeGW([VALID])
    await structured.generate_structured(
        StructuredAnswer, [{"role": "user", "content": "q"}], gw=fake
    )
    system = fake.calls[0][0]
    assert system["role"] == "system" and "json" in system["content"]
    # Literal 在 JSON Schema 里变成 enum，模型能看到合法取值
    assert '"enum"' in system["content"] and '"low"' in system["content"]


async def test_defaults_and_caller_override():
    fake = FakeGW([VALID, VALID])
    msgs = [{"role": "user", "content": "q"}]
    await structured.generate_structured(StructuredAnswer, msgs, gw=fake)
    assert fake.kwargs[0]["response_format"] == {"type": "json_object"}
    assert fake.kwargs[0]["temperature"] == 0.2 and fake.kwargs[0]["max_tokens"] == 1500
    await structured.generate_structured(StructuredAnswer, msgs, gw=fake, temperature=0)
    assert fake.kwargs[1]["temperature"] == 0


async def test_breakdown_nested_schema_roundtrip():
    payload = {
        "title": "文档上传",
        "tasks": [
            {
                "title": "上传接口",
                "type": "backend",
                "estimate_hours": 4,
                "acceptance": "curl 上传 md 返回 201",
            }
        ],
    }
    fake = FakeGW([json.dumps(payload, ensure_ascii=False)])
    data, _ = await structured.generate_structured(
        TaskBreakdown, [{"role": "user", "content": "q"}], gw=fake
    )
    assert isinstance(data.tasks[0], TaskItem) and data.tasks[0].type == "backend"


async def test_invalid_enum_is_rejected_then_repaired():
    bad = json.dumps(
        {
            "title": "t",
            "tasks": [{"title": "a", "type": "devops", "estimate_hours": 1, "acceptance": "x"}],
        },
        ensure_ascii=False,
    )
    good = json.dumps(
        {
            "title": "t",
            "tasks": [{"title": "a", "type": "test", "estimate_hours": 1, "acceptance": "x"}],
        },
        ensure_ascii=False,
    )
    fake = FakeGW([bad, good])
    data, _ = await structured.generate_structured(
        TaskBreakdown, [{"role": "user", "content": "q"}], gw=fake
    )
    assert data.tasks[0].type == "test" and len(fake.calls) == 2
