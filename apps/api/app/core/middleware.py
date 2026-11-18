"""request_id 中间件：透传 / 生成 request_id、写访问日志、兜底 500。

- 传入合法的 `X-Request-ID` 则透传；非法值（含空格 / 引号 / 换行，可日志注入）替换为新 id。
- 未处理异常统一回 `{"error":{"code":"internal_error",...}}`，堆栈只写日志。
"""

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.errors import error_response
from app.core.logging import request_id_var

_VALID_RID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

access_log = logging.getLogger("access")
logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if _VALID_RID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = 500
        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("unhandled error")
                response = error_response(500, "internal server error", "internal_error")
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            access_log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                },
            )
            request_id_var.reset(token)
