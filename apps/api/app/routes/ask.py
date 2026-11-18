"""文档助手 v0（无检索）：把 prompt 渲染 + generate_structured / gateway.stream 拼成 `/v1/ask`。

v0 **故意不接任何知识库**，只依赖模型通用知识，用于 Day14 建立「无检索基线」：
用同一套评测题对比 RAG 上线前后的幻觉率 / 拒答率。
所有响应都带 `source_note`，提醒调用方和评测报告「答案来源只是模型通用知识」。
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.llm.gateway import LLMGateway
from app.llm.prompts import load_prompt
from app.llm.schemas import ChatResult, StructuredAnswer, Usage
from app.llm.structured import StructuredError, generate_structured
from app.routes.chat import sse

router = APIRouter(prefix="/v1", tags=["ask"])
log = logging.getLogger(__name__)

SOURCE_NOTE = "来源：模型通用知识（未接入知识库）"
PROMPT = "qa_answer.v0"


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.gateway


class AskReq(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class AskResp(BaseModel):
    answer: StructuredAnswer
    source_note: str
    prompt: str
    usage: Usage
    cost: float | None = None
    latency_ms: int
    request_id: str = ""


def _messages(question: str) -> list[dict[str, str]]:
    """v0 只放一条业务 system + 一条 user；generate_structured 会在前面再插一条 schema system。"""
    return [
        {"role": "system", "content": load_prompt(PROMPT).render()},
        {"role": "user", "content": question},
    ]


@router.post("/ask", response_model=AskResp)
async def ask(body: AskReq, gw: Annotated[LLMGateway, Depends(get_gateway)]) -> dict:
    try:
        data, res = await generate_structured(StructuredAnswer, _messages(body.question), gw=gw)
    except StructuredError as e:
        # 只回固定 code + 文案：模型原文、schema、校验明细留在服务端日志里
        raise AppError("structured_output_failed", "结构化输出校验失败", 502) from e
    return {
        "answer": data.model_dump(),
        "source_note": SOURCE_NOTE,
        "prompt": load_prompt(PROMPT).ref,
        "usage": res.usage.model_dump(),
        "cost": res.cost,
        "latency_ms": res.latency_ms,
        "request_id": res.request_id,
    }


@router.post("/ask/stream")
async def ask_stream(body: AskReq, gw: Annotated[LLMGateway, Depends(get_gateway)]):
    """流式版输出自然语言（不强制 JSON），done 事件里带上来源说明与用量。"""

    async def gen():
        try:
            async for ev in gw.stream(_messages(body.question)):
                if ev["type"] == "token":
                    yield sse("token", {"text": ev["text"]})
                else:
                    r: ChatResult = ev["result"]
                    yield sse(
                        "done",
                        {
                            "source_note": SOURCE_NOTE,
                            "usage": r.usage.model_dump(),
                            "cost": r.cost,
                            "latency_ms": r.latency_ms,
                            "ttft_ms": r.ttft_ms,
                        },
                    )
        except Exception:
            log.exception("ask stream failed")
            # 不把内部异常细节返回给客户端
            yield sse("error", {"message": "LLM 调用失败，请稍后重试"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
