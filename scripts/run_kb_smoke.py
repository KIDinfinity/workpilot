"""Day18 冒烟：对 `/v1/kb/ask` 跑 `eval/datasets/kb_qa.jsonl`，生成 v0.2 报告。

用法（先另开终端启动 API）：

    cd ~/lab/workpilot/apps/api && uv run uvicorn app.main:app --reload --port 8000
    cd ~/lab/workpilot && uv run --project apps/api python scripts/run_kb_smoke.py

- 启动时用 pydantic 做 schema 校验，不合法直接报错。
- 「来源命中」检查期望来源是否出现在 `retrieved`（top_k 内），W5 细化为 hit@k / MRR。
- 「人工正确」列与统计留空，跑完后人工逐行对照 `expected_answer` 勾选。
- 只读数据集、只写 report/runs，不改产品代码。
"""

import json
import statistics
import time
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
API = "http://localhost:8000/v1/kb/ask"
DATASET = ROOT / "eval/datasets/kb_qa.jsonl"
REFUSAL = "知识库中没有找到"


class QA(BaseModel):
    id: str
    question: str
    type: Literal["in_kb", "out_of_kb", "confusing"]
    expected_answer: str
    expected_sources: list[str]
    tags: list[str] = []


def match(expected: str, hit: dict) -> bool:
    path, _, sec = expected.partition("#")
    return hit["source"] == path and (not sec or sec in hit["section"])


def main() -> None:
    text = DATASET.read_text(encoding="utf-8")
    data = [
        QA.model_validate_json(line) for line in text.splitlines() if line.strip()
    ]  # schema 校验，不合法直接报错
    print(f"schema 校验通过：{len(data)} 题 "
          f"(in_kb={sum(q.type == 'in_kb' for q in data)}, "
          f"out_of_kb={sum(q.type == 'out_of_kb' for q in data)}, "
          f"confusing={sum(q.type == 'confusing' for q in data)})")

    rows = []
    with httpx.Client(timeout=120) as c:
        for q in data:
            try:
                d = c.post(API, json={"question": q.question}).raise_for_status().json()
            except (httpx.HTTPError, ValueError) as e:  # 单题失败不中断全部
                rows.append({"q": q, "hit": None, "refused": None, "n_cite": 0,
                             "top1": "ERR", "latency": 0, "cost": 0.0,
                             "answer": f"ERR: {type(e).__name__}"})
                continue
            if q.expected_sources:
                hit = any(match(e, h) for e in q.expected_sources for h in d["retrieved"])
            else:
                hit = None
            rows.append({
                "q": q, "hit": hit, "refused": d["refused"],
                "n_cite": len(d["citations"]),
                "top1": d["retrieved"][0]["source"] if d["retrieved"] else "-",
                "latency": d["latency_ms"], "cost": d["cost"] or 0.0,
                "answer": d["answer"][:50].replace("\n", " ").replace("|", "/"),
            })

    src = [r for r in rows if r["q"].type != "out_of_kb"]
    ook = [r for r in rows if r["q"].type == "out_of_kb"]
    ok = [r for r in rows if r["refused"] is not None]
    stamp = time.strftime("%Y%m%d")

    head = [
        f"# RAG v0.2 种子集报告 · {stamp}",
        "",
        f"- 来源命中：{sum(r['hit'] for r in src)}/{len(src)}",
        f"- 库外拒答：{sum(r['refused'] for r in ook)}/{len(ook)}",
        (
            f"- 平均延迟：{statistics.mean(r['latency'] for r in ok):.0f} ms；"
            f"总成本：{sum(r['cost'] for r in rows):.6f}"
        ),
        "- 人工正确：__/20（逐行勾选后手填）",
        "",
        "| id | type | 来源命中 | 拒答 | 引用数 | top1 来源 | 答案摘要 | 人工 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    body = [
        f"| {r['q'].id} | {r['q'].type} | "
        f"{'-' if r['hit'] is None else ('✅' if r['hit'] else '❌')} | "
        f"{'是' if r['refused'] else '否'} | {r['n_cite']} | {r['top1']} | "
        f"{r['answer']} | ☐对 ☐错 |"
        for r in rows
    ]
    report = "\n".join(head + body) + "\n"

    path = ROOT / "eval/reports" / f"{stamp}-rag-v0.2.md"
    path.write_text(report, encoding="utf-8")
    runs = ROOT / "eval/runs" / f"{stamp}-rag-v0.2.jsonl"
    serializable = [
        {**{k: v for k, v in r.items() if k != "q"}, "q": r["q"].model_dump()}
        for r in rows
    ]
    runs.write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in serializable) + "\n",
        encoding="utf-8",
    )
    print("\n".join(head[:6]))
    print(f"\n→ 报告 {path}")
    print(f"→ 明细 {runs}")


if __name__ == "__main__":
    main()
