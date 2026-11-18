"""检索：dense（bge-m3）/ hybrid（dense + bm25，RRF 融合）+ metadata 过滤。

`query_points` 是 Qdrant 统一查询入口，hybrid 走 prefetch + FusionQuery。
`search()` 会在 W9 变成 `kb_search` 工具，供 Agent 调用。
"""

from pydantic import BaseModel
from qdrant_client import models

from app.core.config import settings
from app.rag.embedding import embedder
from app.rag.store import store


class Hit(BaseModel):
    chunk_id: str
    score: float
    doc_id: str
    title: str
    section: str
    source: str
    text: str


async def search(
    query: str,
    top_k: int | None = None,
    workspace: str | None = None,
    filters: dict[str, str] | None = None,
    score_threshold: float | None = None,
    collection: str | None = None,
    mode: str | None = None,
) -> list[Hit]:
    ws = workspace or settings.workspace
    name = collection or f"kb_{ws}"
    limit = top_k or settings.top_k
    vec = (await embedder.embed([query]))[0]  # bge-m3 查询无需加指令前缀
    must = [
        models.FieldCondition(key=k, match=models.MatchValue(value=v))
        for k, v in (filters or {}).items()
    ]
    flt = models.Filter(must=must) if must else None

    if (mode or settings.retrieval_mode) == "hybrid":
        # RRF 分数是名次分，与余弦尺度不可比，因此 hybrid 下不使用 score_threshold
        from app.rag.sparse import sparse_query

        prefetch_k = max(20, limit)
        res = await store.client.query_points(
            name,
            prefetch=[
                models.Prefetch(query=vec, using="dense", limit=prefetch_k, filter=flt),
                models.Prefetch(
                    query=sparse_query(query), using="bm25", limit=prefetch_k, filter=flt
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
    else:
        threshold = (
            score_threshold if score_threshold is not None else settings.score_threshold
        )
        res = await store.client.query_points(
            name,
            query=vec,
            limit=limit,
            query_filter=flt,
            score_threshold=threshold,
            with_payload=True,
        )
    payload_keys = ("doc_id", "title", "section", "source", "text")
    return [
        Hit(
            chunk_id=str(p.id),
            score=p.score,
            **{k: str(p.payload.get(k, "")) for k in payload_keys},
        )
        for p in res.points
    ]
