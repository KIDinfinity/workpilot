from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    temperature: float = Field(0.3, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=4096)


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit_tokens: int = 0  # DeepSeek: usage.prompt_cache_hit_tokens


class ChatResult(BaseModel):
    content: str
    model: str
    usage: Usage
    latency_ms: int
    request_id: str = ""
    cost: float | None = None
    ttft_ms: int | None = None          # 首 token 延迟，仅流式
    usage_estimated: bool = False


# ===== Structured Output（Day11）=====
# 下面的模型既是「给前端的响应契约」，也是「注入 system prompt 的 JSON Schema」来源。


class StructuredAnswer(BaseModel):
    """文档助手 v0 的结构化回答。"""

    answer: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list, max_length=8)
    confidence: Literal["low", "mid", "high"]
    needs_more_context: bool


class TaskItem(BaseModel):
    title: str
    type: Literal["frontend", "backend", "test", "doc"]
    estimate_hours: float = Field(gt=0, le=40)
    acceptance: str


class TaskBreakdown(BaseModel):
    """SP-B 预演：需求拆解。"""

    title: str
    tasks: list[TaskItem] = Field(min_length=1, max_length=20)
