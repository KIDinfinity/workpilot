"""KB API：检索 / 带引用回答 / 流式 / 文档列表（Day17）。

安全边界：`workspace` 不允许从请求覆盖，`filters` 只允许白名单 key，为 W19 多空间隔离预留。
"""

import logging
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client import models
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.errors import AppError
from app.core.storage import storage
from app.db.crud import save_turn
from app.db.models import KBDocument
from app.db.session import engine, get_session
from app.llm.gateway import LLMGateway
from app.rag.answer import REFUSAL, KBAnswer, ask, extract_citations, messages_for
from app.rag.jobs import ingest_document
from app.rag.retrieve import search
from app.rag.store import store
from app.routes.chat import sse

router = APIRouter(prefix="/v1/kb", tags=["kb"])
log = logging.getLogger(__name__)

FILTER_KEYS = {"source", "doc_id", "title", "section"}  # workspace 不可从请求覆盖

ALLOWED_EXT = {".md", ".pdf", ".html", ".txt"}
MAX_BYTES = 10 * 1024 * 1024


def clean_filename(name: str | None) -> str:
    name = Path(name or "").name  # 去掉目录部分，防路径穿越
    name = re.sub(r"[^\w.\-]+", "_", name)[:120]  # \w 含中文；其余字符替换为 _
    return name.lstrip(".") or "file"


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.gateway


def _validate_filters(filters: dict[str, str] | None) -> dict[str, str]:
    if not filters:
        return {}
    bad = set(filters) - FILTER_KEYS
    if bad:
        raise AppError("invalid_filter", f"不允许的过滤字段: {sorted(bad)}", 422)
    return filters


class SearchReq(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    filters: dict[str, str] | None = None


class AskReq(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    filters: dict[str, str] | None = None
    conversation_id: str | None = None  # 续问：传入既有会话 id，则追加到该会话


@router.post("/search")
async def kb_search(req: SearchReq) -> list[dict]:
    hits = await search(req.query, top_k=req.top_k, filters=_validate_filters(req.filters))
    return [h.model_dump() for h in hits]


@router.post("/ask", response_model=KBAnswer)
async def kb_ask(
    req: AskReq,
    gw: Annotated[LLMGateway, Depends(get_gateway)],
    s: Annotated[Session, Depends(get_session)],
) -> KBAnswer:
    ans = await ask(req.question, gw, top_k=req.top_k, filters=_validate_filters(req.filters))
    ans.conversation_id, ans.message_id = save_turn(
        s,
        req.conversation_id,
        req.question,
        ans.answer,
        [c.model_dump() for c in ans.citations],
        ans.usage.model_dump() if ans.usage else None,
    )
    return ans


@router.post("/ask/stream")
async def kb_ask_stream(req: AskReq, gw: Annotated[LLMGateway, Depends(get_gateway)]):
    async def gen():
        try:
            filters = _validate_filters(req.filters)
            hits = await search(req.question, top_k=req.top_k, filters=filters)
            hits_data = [h.model_dump(exclude={"text"}) | {"snippet": h.text[:160]} for h in hits]
            yield sse("retrieved", {"hits": hits_data})
            if not hits:
                answer = f"{REFUSAL}与该问题相关的内容。"
                yield sse("token", {"text": answer})
                with Session(engine) as s:  # 流式里不开请求级依赖，独立会话避免清理时机问题
                    cid, mid = save_turn(s, req.conversation_id, req.question, answer, [], None)
                yield sse(
                    "done",
                    {
                        "refused": True,
                        "citations": [],
                        "conversation_id": cid,
                        "message_id": mid,
                    },
                )
                return
            msgs, ref = messages_for(req.question, hits)
            async for ev in gw.stream(msgs, temperature=0.1):
                if ev["type"] == "token":
                    yield sse("token", {"text": ev["text"]})
                else:
                    r = ev["result"]
                    citations = [c.model_dump() for c in extract_citations(r.content, hits)]
                    usage = r.usage.model_dump()
                    # done 之前落库：前端需要 done 里的 message_id 才能提交反馈
                    with Session(engine) as s:
                        cid, mid = save_turn(
                            s, req.conversation_id, req.question, r.content, citations, usage
                        )
                    yield sse(
                        "done",
                        {
                            "refused": r.content.strip().startswith(REFUSAL),
                            "prompt": ref,
                            "citations": citations,
                            "usage": usage,
                            "cost": r.cost,
                            "latency_ms": r.latency_ms,
                            "ttft_ms": r.ttft_ms,
                            "conversation_id": cid,
                            "message_id": mid,
                        },
                    )
        except Exception:
            log.exception("kb ask stream failed")
            yield sse("error", {"message": "LLM 调用失败，请稍后重试"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/upload", status_code=202)
async def kb_upload(
    file: UploadFile,
    bg: BackgroundTasks,
    s: Annotated[Session, Depends(get_session)],
) -> dict:
    filename = clean_filename(file.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, f"unsupported file type: {ext or 'none'}")
    data = await file.read(MAX_BYTES + 1)  # 最多读 10MB+1，避免大文件撑爆内存
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "file too large (max 10MB)")
    if not data:
        raise HTTPException(400, "empty file")
    doc = KBDocument(filename=filename, size=len(data))
    doc.object_key = f"uploads/{doc.id}/{filename}"
    storage.put_bytes(doc.object_key, data)
    s.add(doc)
    s.commit()
    bg.add_task(ingest_document, doc.id)
    return {"id": doc.id, "status": doc.status}


@router.get("/docs", response_model=list[KBDocument])
async def kb_docs(s: Annotated[Session, Depends(get_session)]) -> list[KBDocument]:
    return s.exec(select(KBDocument).order_by(col(KBDocument.created_at).desc())).all()


@router.delete("/docs/{doc_id}", status_code=204)
async def kb_delete_doc(doc_id: str, s: Annotated[Session, Depends(get_session)]) -> None:
    doc = s.get(KBDocument, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    name = f"kb_{settings.workspace}"
    await store.delete_by_doc(name, doc_id)  # 先删 Qdrant 点，避免留下孤儿向量
    if doc.object_key:
        storage.remove(doc.object_key)  # 再删 MinIO 原始对象
    s.delete(doc)
    s.commit()


@router.get("/docs/{doc_id}/chunks")
async def kb_doc_chunks(doc_id: str) -> list[dict]:
    name = f"kb_{settings.workspace}"
    flt = models.Filter(
        must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
    )
    points, _ = await store.client.scroll(
        name, scroll_filter=flt, limit=200, with_payload=True, with_vectors=False
    )
    out = [
        {
            "chunk_index": int((p.payload or {}).get("order", 0)),
            "section": str((p.payload or {}).get("section", "")),
            "text": str((p.payload or {}).get("text", "")),
        }
        for p in points
    ]
    out.sort(key=lambda c: c["chunk_index"])
    return out
