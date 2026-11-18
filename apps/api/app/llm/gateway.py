import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.errors import AppError
from app.llm.pricing import calc_cost, estimate_tokens
from app.llm.schemas import ChatResult, Usage
from app.llm.usage_log import log_call

log = logging.getLogger("workpilot.llm")

# 顺序重要：子类在前（APITimeoutError ⊂ APIConnectionError；Auth/RateLimit ⊂ APIStatusError）
_ERROR_MAP = [
    (APITimeoutError, "llm_timeout", "上游模型响应超时", 504),
    (AuthenticationError, "llm_auth_failed", "上游鉴权失败，请检查 LLM_API_KEY 配置", 502),
    (RateLimitError, "llm_rate_limited", "上游限流，请稍后重试", 503),
    (APIConnectionError, "llm_unavailable", "无法连接上游模型", 502),
    (APIStatusError, "llm_upstream_error", "上游模型返回错误", 502),
]


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError)):
        return True
    return isinstance(exc, APIStatusError) and exc.status_code >= 500


class LLMGateway:
    def __init__(self, settings: Settings, client: Any | None = None, backoff_s: float = 0.5):
        self.model = settings.llm_model_name
        self.max_attempts = settings.llm_max_attempts
        self.timeout = settings.llm_timeout_s
        self.backoff_s = backoff_s  # 测试传 0，免等待
        self._extra_body = settings.llm_extra_body  # 供应商额外字段（豆包默认关思考）
        self._client = client or AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            timeout=settings.llm_timeout_s,
            max_retries=0,  # 关掉 SDK 自带重试，统一由 tenacity 控制
        )

    async def chat(self, messages: list[dict[str, str]], **kw: Any) -> ChatResult:
        start, attempts = time.perf_counter(), 0
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_attempts),
                wait=wait_exponential(multiplier=self.backoff_s, max=8),
                retry=retry_if_exception(_retryable),
                reraise=True,  # 用尽后抛原始异常，而不是 tenacity.RetryError
            ):
                with attempt:
                    attempts = attempt.retry_state.attempt_number
                    resp = await self._client.chat.completions.create(
                        model=self.model, messages=messages, extra_body=self._extra_body, **kw
                    )
        except Exception as e:
            ms = int((time.perf_counter() - start) * 1000)
            for exc_type, code, msg, status in _ERROR_MAP:
                if isinstance(e, exc_type):
                    log.warning(
                        "llm_call status=error code=%s model=%s attempts=%d latency_ms=%d",
                        code,
                        self.model,
                        attempts,
                        ms,
                    )
                    raise AppError(code, msg, status) from e
            raise
        ms = int((time.perf_counter() - start) * 1000)
        usage = resp.usage
        result = ChatResult(
            content=resp.choices[0].message.content or "",
            model=resp.model,
            usage=Usage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
                cache_hit_tokens=getattr(usage, "prompt_cache_hit_tokens", 0) or 0,
            ),
            latency_ms=ms,
            request_id=uuid.uuid4().hex[:12],
        )
        result.cost = calc_cost(result.usage)
        log_call(result, stream=False)
        log.info(
            "llm_call status=ok model=%s attempts=%d latency_ms=%d prompt_tokens=%d "
            "completion_tokens=%d request_id=%s cost=%s",
            result.model,
            attempts,
            ms,
            result.usage.prompt_tokens,
            result.usage.completion_tokens,
            result.request_id,
            result.cost,
        )
        return result  # 注意：日志只记元数据，不记 messages 内容与 key

    async def stream(self, messages: list[dict[str, str]], **extra: Any) -> AsyncIterator[dict]:
        rid, t0, ttft = uuid.uuid4().hex[:12], time.perf_counter(), None
        # 流式不走自动重试：首 token 后无法回滚
        resp = await self._client.chat.completions.create(
            model=self.model, messages=messages, stream=True,
            stream_options={"include_usage": True}, timeout=self.timeout, **extra)
        parts, raw_usage = [], None
        async for chunk in resp:
            if chunk.usage:
                raw_usage = chunk.usage
            if chunk.choices and chunk.choices[0].delta.content:
                if ttft is None:
                    ttft = int((time.perf_counter() - t0) * 1000)
                parts.append(chunk.choices[0].delta.content)
                yield {"type": "token", "text": parts[-1]}
        content = "".join(parts)
        if raw_usage:
            usage = Usage(
                prompt_tokens=raw_usage.prompt_tokens,
                completion_tokens=raw_usage.completion_tokens,
                total_tokens=raw_usage.total_tokens,
                cache_hit_tokens=getattr(raw_usage, "prompt_cache_hit_tokens", 0) or 0,
            )
        else:                                                       # 不支持 include_usage 时估算
            p = sum(estimate_tokens(m["content"]) for m in messages)
            c = estimate_tokens(content)
            usage = Usage(prompt_tokens=p, completion_tokens=c, total_tokens=p + c)
        result = ChatResult(content=content, model=self.model, usage=usage, request_id=rid,
                            latency_ms=int((time.perf_counter() - t0) * 1000), ttft_ms=ttft,
                            cost=calc_cost(usage), usage_estimated=raw_usage is None)
        log_call(result, stream=True)
        log.info(
            "llm_stream status=ok model=%s latency_ms=%d ttft_ms=%d prompt_tokens=%d "
            "completion_tokens=%d request_id=%s cost=%s estimated=%s",
            result.model,
            result.latency_ms,
            result.ttft_ms,
            result.usage.prompt_tokens,
            result.usage.completion_tokens,
            result.request_id,
            result.cost,
            result.usage_estimated,
        )
        yield {"type": "done", "result": result}

    async def aclose(self) -> None:
        await self._client.close()
