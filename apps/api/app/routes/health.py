from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import Settings, get_settings, settings
from app.db.session import get_session
from app.rag.store import store

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: Literal["ok"] = "ok"
    env: str
    version: str


@router.get("/health", response_model=HealthOut)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthOut:
    return HealthOut(env=settings.app_env, version=settings.app_version)


@router.get("/ready")
async def ready(s: Annotated[Session, Depends(get_session)]) -> JSONResponse:
    """readiness：逐项检查依赖，任一失败返回 503。

    - 只回异常类型，不回连接串 / 密钥。
    - compose healthcheck 用 /health（存活），/ready 给部署脚本与人工排障（Day28 不对外暴露）。
    """
    checks: dict[str, str] = {}
    try:
        await store.client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["qdrant"] = f"fail: {type(e).__name__}"
    try:
        s.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["db"] = f"fail: {type(e).__name__}"
    checks["llm_key"] = "ok" if settings.llm_api_key.get_secret_value() else "missing"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "not_ready", "checks": checks},
    )
