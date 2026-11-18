import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel


class DocMeta(BaseModel):
    path: str
    type: Literal["md", "pdf", "html"]
    updated_at: str
    workspace: str = "default"


class Document(BaseModel):
    id: str  # sha256(text)
    source: str  # 相对语料根目录的路径，如 oss/fastapi/query-params.md
    title: str
    text: str
    metadata: DocMeta

    @classmethod
    def create(
        cls,
        *,
        text: str,
        source: str,
        title: str,
        type: Literal["md", "pdf", "html"],
        workspace: str,
        mtime: float,
    ) -> "Document":
        return cls(
            id=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            source=source,
            title=title,
            text=text,
            metadata=DocMeta(
                path=source,
                type=type,
                workspace=workspace,
                updated_at=datetime.fromtimestamp(mtime, UTC).isoformat(),
            ),
        )
