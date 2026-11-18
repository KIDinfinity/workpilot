"""汇总检索实验报告（eval/reports/<stamp>-<glob>.json）为 Markdown 对比表。

用法（仓库根目录或 apps/api 均可，需能 import app）：

    cd ~/lab/workpilot/apps/api
    PYTHONPATH=. uv run python ../../eval/runners/summarize.py --stamp 20261027

- chunks 从 data/index_manifest/<collection>.json 读取（入库时写的事实来源）。
- 只读报告与 manifest，输出 Markdown 到 stdout；`--out` 时写文件。
"""

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def chunks_of(collection: str) -> int | str:
    mf = ROOT / "data" / "index_manifest" / f"{collection}.json"
    if not mf.exists():
        return "-"
    return json.loads(mf.read_text(encoding="utf-8")).get("chunks", "-")


def row(report: dict) -> str:
    cfg, m = report["config"], report["metrics"]
    variant = report["name"].removeprefix("exp-")
    conf = (
        f"c{cfg['chunk_size']}/o{cfg['overlap']}/top{cfg['top_k']}/{cfg['retrieval']}"
    )
    false_refusal = m["false_refusal_in_kb"]
    return (
        f"| {variant} | {conf} | {chunks_of(cfg['collection'])} "
        f"| {m['hit@1']} | {m['hit@3']} | {m['hit@5']} | {m['mrr']} "
        f"| {m['refusal_acc_out_of_kb']} | {'-' if false_refusal is None else false_refusal} "
        f"| {m['retrieve_p95_ms']}ms | {m['answer_p95_ms']}ms | ¥{m['cost_total']:.4f} |"
    )


def build(reports: list[dict], title: str) -> str:
    first = reports[0]
    lines = [
        f"# {title}",
        "",
        f"- 数据：{first['config']['dataset']}（{len(first['rows'])} 题）",
        f"- git sha：`{first['config']['git_sha']}`",
        "",
        "| 变体 | 配置 | chunks | hit@1 | hit@3 | hit@5 | MRR | 拒答正确率 | 库内误拒率 "
        "| 检索P95 | 回答P95 | 成本 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines += [row(r) for r in reports]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="汇总检索实验报告为 Markdown 表")
    ap.add_argument("--stamp", default=time.strftime("%Y%m%d"), help="报告日期戳 YYYYMMDD")
    ap.add_argument("--pattern", default="exp-*", help="报告名 glob（默认 exp-*）")
    ap.add_argument("--exclude", default=None, help="排除的报告名 glob（如 exp-*-k*）")
    ap.add_argument("--out", type=Path, default=None, help="写入的 Markdown 路径（默认 stdout）")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    files = sorted((ROOT / "eval/reports").glob(f"{args.stamp}-{args.pattern}.json"))
    if args.exclude:
        pattern = f"{args.stamp}-{args.exclude}.json"
        files = [f for f in files if not f.match(pattern)]
    if not files:
        raise SystemExit(f"没有匹配的报告：eval/reports/{args.stamp}-{args.pattern}.json")

    reports = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    md = build(reports, args.title or f"{args.stamp} 检索实验汇总")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"→ MD {args.out}")
    else:
        print(md)


if __name__ == "__main__":
    main()
