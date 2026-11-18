import json
import time

from app.core.config import get_settings
from app.llm.schemas import ChatResult


def log_call(
    result: ChatResult, *, stream: bool, ok: bool = True, error: str | None = None
) -> None:
    s = get_settings()
    path = s.llm_log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "request_id": result.request_id,
        "model": result.model,
        "stream": stream,
        "ok": ok,
        "error": error,
        "prompt_tokens": result.usage.prompt_tokens,
        "completion_tokens": result.usage.completion_tokens,
        "cache_hit_tokens": result.usage.cache_hit_tokens,
        "usage_estimated": result.usage_estimated,
        "cost": result.cost,
        "currency": s.price_currency,
        "latency_ms": result.latency_ms,
        "ttft_ms": result.ttft_ms,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
