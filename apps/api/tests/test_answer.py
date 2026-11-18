"""answer.py 单测：不触真实 LLM 与真实检索。"""

from app.core.config import settings
from app.llm.schemas import ChatResult, Usage
from app.rag.answer import REFUSAL, ask, build_context, extract_citations
from app.rag.retrieve import Hit


def _hits(n: int = 3) -> list[Hit]:
    return [
        Hit(
            chunk_id=f"c{i}",
            score=round(0.8 - i * 0.01, 4),
            doc_id=f"d{i}",
            title=f"文档{i}",
            section=f"第{i}节",
            source=f"src{i}.md",
            text=f"内容{i}",
        )
        for i in range(1, n + 1)
    ]


class FakeGW:
    def __init__(self, content: str = "") -> None:
        self.content = content
        self.called = False

    async def chat(self, messages, **kw):
        self.called = True
        return ChatResult(
            content=self.content,
            model="fake",
            usage=Usage(prompt_tokens=12, completion_tokens=8, total_tokens=20),
            latency_ms=42,
            request_id="req-1",
            cost=0.000123,
        )


def test_extract_citations_filters_out_of_range():
    cites = extract_citations("结论 [1][3]，另见 [9]", _hits(3))
    assert [c.n for c in cites] == [1, 3]


def test_build_context_starts_at_1_and_has_section():
    ctx = build_context(_hits(2))
    assert ctx.startswith("[1] 《文档1》 第1节")
    assert "[2] 《文档2》 第2节" in ctx


async def test_ask_empty_retrieval_refuses_without_llm(monkeypatch):
    async def fake_search(question, **kw):
        return []

    monkeypatch.setattr("app.rag.answer.search", fake_search)
    gw = FakeGW()
    ans = await ask("随便什么", gw)
    assert ans.refused is True
    assert ans.answer.startswith(REFUSAL)
    assert ans.citations == []
    assert gw.called is False  # 空检索直接拒答，不调 LLM


async def test_ask_model_refusal(monkeypatch):
    async def fake_search(question, **kw):
        return _hits(2)

    monkeypatch.setattr("app.rag.answer.search", fake_search)
    ans = await ask("问题", FakeGW(f"{REFUSAL}与该问题相关的内容。"))
    assert ans.refused is True
    assert ans.citations == []
    assert ans.prompt == settings.answer_prompt
