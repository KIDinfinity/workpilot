"""Day19 Step1：LLM 生成候选评测题（llm_seed）。

从 Qdrant `kb_default` 抽样 40 个 chunk，用 `prompts/seed_question.v1.md` 逐条让 LLM
出题，`answerable=true` 的写入 `eval/datasets/kb_qa.candidates.jsonl`，供人工审核。

用法（必须在 apps/api 目录下，PYTHONPATH=. 才能 import app.*）：

    cd ~/lab/workpilot/apps/api && PYTHONPATH=. uv run python ../../scripts/seed_eval.py --n 40

- 只读 Qdrant，只写 candidates 文件，不改产品代码。
- 生成失败 / answerable=false 直接跳过，不重试（成本可控）。
"""

import argparse
import asyncio
import json
import random

from pydantic import BaseModel, Field

from app.core.config import ROOT_DIR, settings
from app.llm.gateway import LLMGateway
from app.llm.prompts import load_prompt
from app.llm.structured import StructuredError, generate_structured
from app.rag.store import store


class SeedQuestion(BaseModel):
    question: str = Field(min_length=2)
    expected_answer: str = Field(min_length=1, max_length=120)
    answerable: bool


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="LLM 生成候选评测题")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--collection", default="kb_default")
    ap.add_argument("--out", default=str(ROOT_DIR / "eval/datasets/kb_qa.candidates.jsonl"))
    return ap.parse_args()


async def main() -> None:
    a = parse_args()
    points, _ = await store.client.scroll(a.collection, limit=500, with_payload=True)
    sampled = random.Random(42).sample(points, min(a.n, len(points)))
    gw = LLMGateway(settings)
    prompt = load_prompt("seed_question.v1")
    out_path = a.out
    wrote, skipped = 0, 0
    with open(out_path, "w", encoding="utf-8") as f:
        for i, p in enumerate(sampled, 1):
            pl = p.payload
            source = pl.get("source", "")
            section = pl.get("section", "")
            title = pl.get("title", "")
            text = pl.get("text", "")
            if not text.strip():
                skipped += 1
                continue
            try:
                obj, _ = await generate_structured(
                    SeedQuestion,
                    [{"role": "user", "content": prompt.render(title=title, section=section, text=text)}],
                    gw=gw,
                )
            except StructuredError as e:
                print(f"[{i}/{len(sampled)}] skip 结构化失败 {source}#{section}: {e}")
                skipped += 1
                continue
            if not obj.answerable:
                skipped += 1
                continue
            rec = {
                "id": f"cand{wrote + 1:03d}",
                "question": obj.question.strip(),
                "expected_answer": obj.expected_answer.strip(),
                "type": "in_kb",
                "expected_sources": [f"{source}#{section}"],
                "tags": ["llm_seed"],
                "title": title,
                "section": section,
                "seed_text": text[:400],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            wrote += 1
            print(f"[{i}/{len(sampled)}] ok {source}#{section}: {obj.question[:40]}")
    print(f"candidates={wrote} skipped={skipped} -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
