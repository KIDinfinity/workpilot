"""JSON 结构化日志 + 基于 contextvars 的 request_id 透传。

- `request_id_var` 按 asyncio 任务隔离：任意深度的函数都能读到当前请求的 id，无需层层传参。
- `RequestIdFilter` 给每条 LogRecord 注入 request_id；`JsonFormatter` 输出一行 JSON。
- 堆栈只进日志、不进响应；密钥从不进日志。
"""

import json
import logging
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_EXTRA_KEYS = ("method", "path", "status", "latency_ms", "model", "tokens", "doc_id")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        payload.update({k: getattr(record, k) for k in _EXTRA_KEYS if hasattr(record, k)})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_logs: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        JsonFormatter()
        if json_logs
        else logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # 用我们自己的访问日志（access）替代 uvicorn.access，避免重复且格式不一致
    logging.getLogger("uvicorn.access").disabled = True
