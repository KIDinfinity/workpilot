"""Day14 冒烟：对 `/v1/ask` 跑 `eval/datasets/smoke_v0.jsonl`，生成 Markdown 报告。

用法（先另开终端启动 API）：

    cd ~/lab/workpilot/apps/api && uv run uvicorn app.main:app --reload --port 8000
    cd ~/lab/workpilot && uv run --project apps/api python eval/runners/run_smoke.py 20261015

- 唯一可选参数是报告日期戳 `YYYYMMDD`，缺省用今天。
  产物：报告 `eval/reports/<YYYYMMDD>-smoke-v0.1.md`（提交）+ 明细
  `eval/runs/<YYYYMMDD>-smoke-v0.1.jsonl`（含完整答案，忽略）。
- 「人工判定」列留空待人工对照 `expected` 勾选；统计行只统计 HTTP 200 的样本。
- 只读数据集、只写 report/runs，不改任何产品代码。
"""

import json
import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
API = "http://localhost:8000/v1/ask"
DATASET = ROOT / "eval/datasets/smoke_v0.jsonl"


def load_rows() -> list[dict]:
    text = DATASET.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def call_api(client: httpx.Client, row: dict) -> dict:
    resp = client.post(API, json={"question": row["question"]})
    if resp.status_code != 200:
        return {**row, "status": resp.status_code}
    d = resp.json()
    return {
        **row,
        "status": 200,
        "summary": d["answer"]["answer"][:60].replace("\n", " "),
        "full_answer": d["answer"]["answer"],
        "key_points": d["answer"]["key_points"],
        "confidence": d["answer"]["confidence"],
        "needs_more_context": d["answer"]["needs_more_context"],
        "latency_ms": d["latency_ms"],
        "cost": d["cost"] or 0.0,
        "request_id": d["request_id"],
    }


def render(rows: list[dict], stamp: str) -> str:
    ok = [o for o in rows if o["status"] == 200]
    lines = [
        f"# Smoke v0.1 · {stamp}",
        "",
        "| id | type | 答案摘要 | 置信度 | 延迟ms | 成本 | 人工判定 |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {o['id']} | {o['type']} | {o.get('summary', 'ERR')} | {o.get('confidence', '-')} | "
        f"{o.get('latency_ms', '-')} | {o.get('cost', '-')} | ☐对 ☐错 ☐幻觉 |"
        for o in rows
    ]
    if ok:
        stat = (
            f"- 成功 {len(ok)}/{len(rows)}；平均延迟 "
            f"{statistics.mean(o['latency_ms'] for o in ok):.0f} ms；"
            f"总成本 {sum(o['cost'] for o in ok):.6f}；low 置信占比 "
            f"{sum(o['confidence'] == 'low' for o in ok) / len(ok):.0%}"
        )
    else:
        stat = f"- 成功 0/{len(rows)}（全部失败，先检查 API 是否启动、密钥是否可用）"
    return "\n".join([*lines, "", stat]) + "\n"


def main() -> None:
    stamp = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d")
    rows = load_rows()
    with httpx.Client(timeout=90) as client:
        out = [call_api(client, r) for r in rows]
    # 运行明细（含完整答案）→ eval/runs/（.gitignore 忽略），供人工判定与 badcase 取证
    runs = ROOT / "eval/runs" / f"{stamp}-smoke-v0.1.jsonl"
    runs.parent.mkdir(parents=True, exist_ok=True)
    runs.write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n",
        encoding="utf-8",
    )
    report = ROOT / "eval/reports" / f"{stamp}-smoke-v0.1.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render(out, stamp), encoding="utf-8")
    print(render(out, stamp))
    print(f"[report] {report}")
    print(f"[runs]   {runs}")


if __name__ == "__main__":
    main()
