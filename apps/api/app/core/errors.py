"""统一错误格式：`{"error": {"code", "message", "request_id"}}` + `X-Request-ID` 响应头。

- AppError：业务可预期错误（对外只暴露 code + message，不带堆栈 / 上游原文 / 密钥）。
- StarletteHTTPException：404 / 405 等框架级错误。
- RequestValidationError：422，只回显字段路径、不回显用户输入值。
- 未处理异常由 RequestIdMiddleware 兜底成 500。
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    503: "unavailable",
}


class AppError(Exception):
    """可预期错误：对外只暴露 code + message，不带堆栈、上游原文和密钥。"""

    def __init__(self, code: str, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


def error_response(status: int, message: str, code: str | None = None) -> JSONResponse:
    rid = request_id_var.get()
    return JSONResponse(
        status_code=status,
        headers={"X-Request-ID": rid},
        content={
            "error": {
                "code": code or _CODES.get(status, "error"),
                "message": message,
                "request_id": rid,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.message, exc.code)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = ", ".join(".".join(str(p) for p in e["loc"]) for e in exc.errors())
        return error_response(422, f"invalid request fields: {fields}")
