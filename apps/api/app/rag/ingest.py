import argparse
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.core.config import ROOT_DIR, settings
from app.rag.chunking import chunk_document
from app.rag.embedding import embedder
from app.rag.loaders import load_dir
from app.rag.models import Document
from app.rag.store import store


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="WorkPilot ingest")
    ap.add_argument("--path", type=Path, required=True)
    ap.add_argument("--workspace", default="default")
    ap.add_argument(
        "--config", type=Path, default=None, help="YAML 变体配置（CLI > YAML > settings）"
    )
    ap.add_argument("--collection", default=None, help="默认 kb_{workspace}")
    ap.add_argument("--chunk-size", type=int, default=None)
    ap.add_argument("--overlap", type=int, default=None)
    ap.add_argument("--retrieval", choices=["dense", "hybrid"], default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--upload-raw", action="store_true", help="P1：原始文件上传 MinIO")
    return ap.parse_args()


def resolve_config(a: argparse.Namespace) -> dict:
    """优先级：命令行 > YAML > settings。"""
    cfg = {
        "collection": None,
        "chunk_size": settings.chunk_size,
        "overlap": settings.chunk_overlap,
        "retrieval": settings.retrieval_mode,
    }
    if a.config:
        y = yaml.safe_load(a.config.read_text(encoding="utf-8")) or {}
        for key in ("collection", "chunk_size", "retrieval"):
            if y.get(key) is not None:
                cfg[key] = y[key]
        if y.get("chunk_overlap") is not None:
            cfg["overlap"] = y["chunk_overlap"]
        elif y.get("overlap") is not None:
            cfg["overlap"] = y["overlap"]
    for key, val in (
        ("collection", a.collection),
        ("chunk_size", a.chunk_size),
        ("overlap", a.overlap),
        ("retrieval", a.retrieval),
    ):
        if val is not None:
            cfg[key] = val
    return cfg


def upload_raw(root: Path, workspace: str, docs: list[Document]) -> int:
    import boto3

    from app.core.config import get_settings

    s = get_settings()
    s3 = boto3.client(
        "s3",
        endpoint_url=s.minio_endpoint,
        aws_access_key_id=s.minio_access_key,
        aws_secret_access_key=s.minio_secret_key.get_secret_value(),
        region_name="us-east-1",
    )
    bucket = "workpilot-raw"
    existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    if bucket not in existing:
        s3.create_bucket(Bucket=bucket)
    n = 0
    for d in docs:
        abs_path = root / d.source
        key = f"{workspace}/{d.id}/{Path(d.source).name}"
        s3.upload_file(str(abs_path), bucket, key)
        n += 1
    return n


async def main() -> None:
    a = parse_args()
    cfg = resolve_config(a)
    root = a.path.resolve()
    docs, dup = load_dir(root, a.workspace)
    types = Counter(d.metadata.type for d in docs)
    chars = sum(len(d.text) for d in docs)
    print(
        f"docs={len(docs)} dup_skipped={dup} chars={chars} "
        f"avg={chars // max(len(docs), 1)} types={dict(types)}"
    )
    print(
        f"config: collection={cfg['collection'] or f'kb_{a.workspace}'} "
        f"chunk_size={cfg['chunk_size']} overlap={cfg['overlap']} retrieval={cfg['retrieval']}"
    )
    for d in sorted(docs, key=lambda d: len(d.text))[:3]:
        print(f"  最短: {d.source} ({len(d.text)} chars)")  # 检查是否有抽取失败的空壳文档
    if a.dry_run:
        return
    if a.upload_raw:
        n = upload_raw(root, a.workspace, docs)
        print(f"uploaded={n} to MinIO bucket workpilot-raw")

    # Day16：chunk → embed → upsert（幂等：先算完向量再按 source 删旧点，失败时不丢旧数据）
    name = cfg["collection"] or f"kb_{a.workspace}"
    hybrid = cfg["retrieval"] == "hybrid"
    await store.ensure_collection(name, settings.embed_dim, hybrid=hybrid)
    total = 0
    for i, doc in enumerate(docs, 1):
        chunks = chunk_document(doc, cfg["chunk_size"], cfg["overlap"])
        if not chunks:
            continue
        texts = [f"{doc.title} / {c.section}\n{c.text}" for c in chunks]
        vecs = await embedder.embed(texts)
        svs = None
        if hybrid:
            from app.rag.sparse import sparse_docs

            svs = sparse_docs(texts)
        await store.delete_by_source(name, doc.source)
        await store.upsert(name, doc, chunks, vecs, svs)
        total += len(chunks)
        print(f"[{i}/{len(docs)}] {doc.source} → {len(chunks)} chunks")
    points = await store.count(name)
    print(f"docs={len(docs)} chunks={total} points={points} collection={name}")

    # P1：写 manifest，W5 评测报告的配置快照从这里读
    manifest_dir = ROOT_DIR / "data" / "index_manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "collection": name,
        "chunk_size": cfg["chunk_size"],
        "overlap": cfg["overlap"],
        "retrieval": cfg["retrieval"],
        "embed_model": settings.embedding_model,
        "docs": len(docs),
        "chunks": total,
        "points": points,
        "corpus_path": str(root),
        "created_at": datetime.now(UTC).isoformat(),
    }
    (manifest_dir / f"{name}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"manifest={manifest_dir / f'{name}.json'}")


if __name__ == "__main__":
    asyncio.run(main())
