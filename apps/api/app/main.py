import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.db.session import init_db
from app.llm.gateway import LLMGateway
from app.routes import ask, chat, conversations, health, kb, structured


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # 启动建表（只建不存在的表；W19 换 Alembic）
    app.state.gateway = LLMGateway(get_settings())  # 进程级单例，复用 HTTP 连接池
    yield
    await app.state.gateway.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_json)
    for noisy in ("httpx", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    app = FastAPI(title="WorkPilot API", version=settings.app_version, lifespan=lifespan)
    register_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(structured.router)
    app.include_router(ask.router)
    app.include_router(kb.router)
    app.include_router(conversations.router)
    return app


app = create_app()
