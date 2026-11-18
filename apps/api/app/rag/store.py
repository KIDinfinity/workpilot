from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.rag.chunking import Chunk
from app.rag.models import Document


class QdrantStore:
    def __init__(self, url: str = settings.qdrant_url) -> None:
        self.client = AsyncQdrantClient(url=url)

    async def ensure_collection(self, name: str, size: int = 1024, hybrid: bool = False) -> None:
        if await self.client.collection_exists(name):
            return
        if hybrid:
            # 命名向量：dense 语义 + bm25 稀疏，查询侧用 prefetch + RRF 融合
            await self.client.create_collection(
                name,
                vectors_config={
                    "dense": models.VectorParams(size=size, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
        else:
            await self.client.create_collection(
                name, vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE)
            )
        for key in ("doc_id", "source", "workspace"):
            await self.client.create_payload_index(
                name, field_name=key, field_schema=models.PayloadSchemaType.KEYWORD
            )

    async def upsert(
        self,
        name: str,
        doc: Document,
        chunks: list[Chunk],
        vectors: list[list[float]],
        sparse: list[models.SparseVector] | None = None,
    ) -> None:
        points = [
            models.PointStruct(
                id=c.id,
                vector={"dense": v, "bm25": sv} if sparse is not None else v,
                payload={
                    "doc_id": c.doc_id,
                    "title": doc.title,
                    "source": doc.source,
                    "section": c.section,
                    "text": c.text,
                    "order": c.order,
                    "workspace": doc.metadata.workspace,
                },
            )
            for i, (c, v) in enumerate(zip(chunks, vectors, strict=True))
            if sparse is None or (sv := sparse[i]) is not None
        ]
        await self.client.upsert(name, points=points, wait=True)

    async def _delete(self, name: str, key: str, value: str) -> None:
        flt = models.Filter(
            must=[models.FieldCondition(key=key, match=models.MatchValue(value=value))]
        )
        await self.client.delete(name, points_selector=models.FilterSelector(filter=flt), wait=True)

    async def delete_by_doc(self, name: str, doc_id: str) -> None:
        await self._delete(name, "doc_id", doc_id)

    async def delete_by_source(self, name: str, source: str) -> None:
        await self._delete(name, "source", source)

    async def count(self, name: str) -> int:
        return (await self.client.count(name, exact=True)).count


store = QdrantStore()
