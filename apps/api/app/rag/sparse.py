"""稀疏向量（BM25）：fastembed 本地分词 + IDF，用于 hybrid 检索的关键词侧。

懒加载：只有 hybrid 路径才 import fastembed / 下载模型，dense 流程不依赖它。
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from qdrant_client import models

if TYPE_CHECKING:
    from fastembed import SparseTextEmbedding


@lru_cache
def _bm25() -> "SparseTextEmbedding":
    from fastembed import SparseTextEmbedding

    return SparseTextEmbedding(model_name="Qdrant/bm25")  # 首次会下载小模型文件


def _to_qdrant(e) -> models.SparseVector:
    return models.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())


def sparse_docs(texts: list[str]) -> list[models.SparseVector]:
    return [_to_qdrant(e) for e in _bm25().embed(texts)]


def sparse_query(text: str) -> models.SparseVector:
    return _to_qdrant(next(iter(_bm25().query_embed(text))))
