"""知识库后台导入任务（Day25）。

把 W4 的 Ingest → Chunk → Embed → Upsert 管线包装成「文档状态机」：
上传路由把原始文件写入 MinIO + 落一条 pending 记录后，用 FastAPI BackgroundTasks
在响应返回后调用本文件的 `ingest_document`，把状态推进到 processing → ready/failed。

单机 Demo 用 BackgroundTasks（同进程）；W19 再评估队列（Celery/Redis）。
"""

import logging
import tempfile
from pathlib import Path

from sqlmodel import Session

from app.core.config import settings
from app.core.storage import storage
from app.db.models import KBDocument, utcnow
from app.db.session import engine
from app.rag.chunking import chunk_document
from app.rag.embedding import embedder
from app.rag.loaders import load_file
from app.rag.store import store

logger = logging.getLogger(__name__)


async def ingest_document(doc_id: str) -> None:
    """读取 MinIO 原始文件 → 解析 → 分块 → 向量化入库，落最终状态。"""
    with Session(engine) as s:
        doc = s.get(KBDocument, doc_id)
        if doc is None:
            return
        doc.status = "processing"
        s.add(doc)
        s.commit()
        try:
            data = storage.get_bytes(doc.object_key)
            suffix = Path(doc.filename).suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                tmp.flush()
                tmp_path = tmp.name
            try:
                d = load_file(Path(tmp_path), doc_id=doc.id, title=doc.filename)
                if d is None:
                    raise ValueError("unsupported or empty file")
                chunks = chunk_document(d, settings.chunk_size, settings.chunk_overlap)
                if not chunks:
                    raise ValueError("no chunks produced")
                name = f"kb_{settings.workspace}"
                await store.ensure_collection(name, settings.embed_dim)
                texts = [f"{d.title} / {c.section}\n{c.text}" for c in chunks]
                vecs = await embedder.embed(texts)
                await store.upsert(name, d, chunks, vecs)
                doc.chunks = len(chunks)
                doc.status, doc.error = "ready", None
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:  # 后台任务无人接异常，必须自己落状态
            logger.exception("ingest failed doc_id=%s", doc_id)
            doc.status, doc.error = "failed", f"{type(e).__name__}: {e}"[:500]
        doc.updated_at = utcnow()
        s.add(doc)
        s.commit()
