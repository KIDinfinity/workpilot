"""带引用回答：检索 → 编号上下文 → 只依据上下文作答并用 [n] 引用 → 不足则拒答。

两层拒答：
① 检索无结果 / 全部低于阈值 → 直接拒答，不调 LLM（省成本、零幻觉）；
② 有结果但不相关 → prompt 规则让模型拒答。

引用解析只信任编号，来源信息（标题 / 段落 / 链接）由程序回映射，不让模型编。
"""

import re
import time

from pydantic import BaseModel

from app.core.config import settings
from app.llm.gateway import LLMGateway
from app.llm.prompts import load_prompt
from app.llm.schemas import Usage
from app.rag.retrieve import Hit, search

REFUSAL = "知识库中没有找到"
_CITE = re.compile(r"\[(\d{1,2})\]")


class Citation(BaseModel):
    n: int
    doc_title: str
    section: str
    source: str
    snippet: str
    score: float


class KBAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved: list[Hit]
    refused: bool
    prompt: str
    usage: Usage | None = None
    cost: float | None = None
    latency_ms: int
    conversation_id: str | None = None   # Day24 落库后回填（仅 /v1/kb/ask 非流式）
    message_id: str | None = None


def build_context(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{i}] 《{h.title}》 {h.section}\n{h.text}" for i, h in enumerate(hits, 1))


def extract_citations(answer: str, hits: list[Hit]) -> list[Citation]:
    # 过滤越界编号：模型可能写出不存在的 [9]，越界次数是「引用错误」badcase 信号
    ns = sorted({int(n) for n in _CITE.findall(answer) if 1 <= int(n) <= len(hits)})
    return [
        Citation(
            n=n,
            doc_title=hits[n - 1].title,
            section=hits[n - 1].section,
            source=hits[n - 1].source,
            snippet=hits[n - 1].text[:160],
            score=round(hits[n - 1].score, 4),
        )
        for n in ns
    ]


def messages_for(question: str, hits: list[Hit]) -> tuple[list[dict], str]:
    p = load_prompt(settings.answer_prompt)
    return (
        [
            {"role": "system", "content": p.render(context=build_context(hits))},
            {"role": "user", "content": question},
        ],
        p.ref,
    )


async def ask(question: str, gw: LLMGateway, **search_kw) -> KBAnswer:
    t0 = time.perf_counter()
    hits = await search(question, **search_kw)
    if not hits:  # 第一层拒答：不调 LLM
        return KBAnswer(
            answer=f"{REFUSAL}与该问题相关的内容。",
            citations=[],
            retrieved=[],
            refused=True,
            prompt="-",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
    msgs, ref = messages_for(question, hits)
    res = await gw.chat(msgs, temperature=0.1)
    text = res.content.strip()
    return KBAnswer(
        answer=text,
        citations=extract_citations(text, hits),
        retrieved=hits,
        refused=text.startswith(REFUSAL),
        prompt=ref,
        usage=res.usage,
        cost=res.cost,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
