"""结构化输出路由：把 prompt 渲染 + generate_structured 拼成对外 HTTP 接口。

对外契约固定为 `{"data": ..., "prompt": "<id>.v<N>", "usage": ..., "latency_ms": ...}`，
其中 `prompt` 让每个调用方 / 评测报告都能追溯用的是哪一版 prompt。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.llm.gateway import LLMGateway
from app.llm.prompts import load_prompt
from app.llm.schemas import ChatResult, StructuredAnswer, TaskBreakdown, Usage
from app.llm.structured import StructuredError, generate_structured

router = APIRouter(prefix="/v1/structured", tags=["structured"])

PROMPT_ANSWER = "structured_answer.v1"
PROMPT_BREAKDOWN = "task_breakdown.v1"


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.gateway


class AnswerReq(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    context: str = Field("", max_length=8000)


class BreakdownReq(BaseModel):
    requirement: str = Field(min_length=1, max_length=2000)
    stack: str = Field("React + FastAPI", max_length=200)


class AnswerResp(BaseModel):
    data: StructuredAnswer
    prompt: str
    usage: Usage
    latency_ms: int


class BreakdownResp(BaseModel):
    data: TaskBreakdown
    prompt: str
    usage: Usage
    latency_ms: int


def _envelope(data: BaseModel, prompt_ref: str, res: ChatResult) -> dict:
    body = {
        "data": data.model_dump(),
        "prompt": prompt_ref,
        "usage": res.usage.model_dump(),
        "latency_ms": res.latency_ms,
    }
    return body


@router.post("/answer", response_model=AnswerResp)
async def structured_answer(
    body: AnswerReq, gw: Annotated[LLMGateway, Depends(get_gateway)]
) -> dict:
    p = load_prompt(PROMPT_ANSWER)
    text = p.render(question=body.question, context=body.context or "（无）")
    try:
        data, res = await generate_structured(
            StructuredAnswer, [{"role": "user", "content": text}], gw=gw
        )
    except StructuredError as e:
        # 只回 code + 固定文案：模型原文、schema、错误明细都不外泄，细节留在服务端日志里
        raise AppError("structured_output_failed", "结构化输出校验失败", 502) from e
    return _envelope(data, p.ref, res)


@router.post("/breakdown", response_model=BreakdownResp)
async def structured_breakdown(
    body: BreakdownReq, gw: Annotated[LLMGateway, Depends(get_gateway)]
) -> dict:
    p = load_prompt(PROMPT_BREAKDOWN)
    text = p.render(requirement=body.requirement, stack=body.stack)
    try:
        data, res = await generate_structured(
            TaskBreakdown, [{"role": "user", "content": text}], gw=gw
        )
    except StructuredError as e:
        raise AppError("structured_output_failed", "结构化输出校验失败", 502) from e
    return _envelope(data, p.ref, res)
