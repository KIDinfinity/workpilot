"""SQLModel 引擎与会话管理。

- SQLite 单机单用户足够；W19 换 Postgres 只改 `database_url` + 迁移工具。
- 流式生成器里**不要复用依赖注入的 Session**，自己 `with Session(engine)` 开新的。
"""

from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


def init_db() -> None:
    """W6–W18：create_all；W19 换 Postgres 后改为 Alembic 迁移。"""
    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(
            parents=True, exist_ok=True
        )
    from app.db import models  # noqa: F401  确保模型已注册到 metadata

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
