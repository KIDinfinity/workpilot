"""Day19：RAG 检索指标 runner —— 一条命令算 hit@k / MRR / 拒答 / 延迟 / 成本。

从仓库根目录运行 `make eval-rag`，可直接 import `app.*`：

- 检索指标固定 top10、`score_threshold=0.0`（与线上 top_k 解耦，不受阈值影响）。
- 库外题（out_of_kb）始终走生成以测拒答；`--with-answer` 时库内题也生成（Day21 judge 用）。
- 只读数据集、只写 `eval/reports/*.json` 与 `.md`，不改产品代码。
"""

import argparse
import asyncio
import json
import math
import statistics
import subprocess
import time
from pathlib import Path

import yaml
from judge import JudgeResult, agreement, judge_one

from app.core.config import ROOT_DIR, settings
from app.llm.gateway import LLMGateway
from app.rag.answer import ask, build_context
from app.rag.retrieve import search


def match(expected: str, hit) -> bool:
    path, _, sec = expected.partition("#")
    return hit.source == path and (not sec or sec in hit.section)


def first_rank(expected: list[str], hits) -> int | None:
    return next((i for i, h in enumerate(hits, 1) if any(match(e, h) for e in expected)), None)


def pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    return s[max(0, math.ceil(p * len(s)) - 1)] if s else 0.0


def snapshot(cfg: dict) -> dict:
    mf = ROOT_DIR / "data" / "index_manifest" / f"{cfg['collection']}.json"
    manifest = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
    ).stdout.strip()
    return {
        "collection": cfg["collection"],
        "chunk_size": manifest.get("chunk_size", settings.chunk_size),
        "overlap": manifest.get("overlap", settings.chunk_overlap),
        "top_k": cfg["top_k"],
        "retrieval": cfg.get("retrieval", "dense"),
        "score_threshold": settings.score_threshold,
        "embed_model": manifest.get("embed_model", settings.embedding_model),
        "answer_prompt": settings.answer_prompt,
        "git_sha": sha,
        "dataset": cfg["dataset"],
    }


async def run(cfg: dict) -> dict:
    lines = Path(cfg["dataset"]).read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    gold_path = ROOT_DIR / "eval/datasets/judge_gold.jsonl"
    gold = (
        [
            json.loads(line)
            for line in gold_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if gold_path.exists()
        else []
    )
    gw = LLMGateway(settings)
    out = []
    for q in rows:
        t0 = time.perf_counter()
        hits = await search(
            q["question"],
            top_k=10,
            collection=cfg["collection"],
            score_threshold=0.0,
            mode=cfg.get("retrieval", "dense"),
        )
        r = {
            "id": q["id"],
            "type": q["type"],
            "retrieve_ms": int((time.perf_counter() - t0) * 1000),
            "top1_score": round(hits[0].score, 4) if hits else 0.0,
            "rank": first_rank(q["expected_sources"], hits) if q["expected_sources"] else None,
            "top3": [f"{h.source}#{h.section}" for h in hits[:3]],
        }
        if cfg["with_answer"] or q["type"] == "out_of_kb":
            a = await ask(
                q["question"],
                gw,
                top_k=cfg["top_k"],
                collection=cfg["collection"],
                mode=cfg.get("retrieval", "dense"),
            )
            r |= {
                "refused": a.refused,
                "answer": a.answer,
                "answer_ms": a.latency_ms,
                "cost": a.cost or 0.0,
                "citations": [c.n for c in a.citations],
                "context": build_context(a.retrieved),
            }
            if cfg["judge"]:
                judged, judge_cost = await judge_one(
                    q["question"],
                    q["expected_answer"],
                    build_context(a.retrieved),
                    a.answer,
                    gw,
                )
                r["judge"] = judged.model_dump()
                r["judge_cost"] = judge_cost or 0.0
        out.append(r)
    await gw.aclose()

    ranked = [r for r in out if r["type"] != "out_of_kb"]
    ook = [r for r in out if r["type"] == "out_of_kb"]
    inkb_ans = [r for r in ranked if "refused" in r]

    m = {
        f"hit@{k}": round(sum(1 for r in ranked if r["rank"] and r["rank"] <= k) / len(ranked), 3)
        for k in (1, 3, 5)
    }
    m |= {
        "mrr": round(sum(1 / r["rank"] for r in ranked if r["rank"]) / len(ranked), 3),
        "refusal_acc_out_of_kb": round(sum(r["refused"] for r in ook) / len(ook), 3),
        "false_refusal_in_kb": (
            round(sum(r["refused"] for r in inkb_ans) / len(inkb_ans), 3) if inkb_ans else None
        ),
        "retrieve_p50_ms": pct([r["retrieve_ms"] for r in out], 0.5),
        "retrieve_p95_ms": pct([r["retrieve_ms"] for r in out], 0.95),
        "answer_p95_ms": pct([r["answer_ms"] for r in out if "answer_ms" in r], 0.95),
        "cost_total": round(sum(r.get("cost", 0) for r in out), 6),
        "top1_mean_in_kb": round(statistics.mean(r["top1_score"] for r in ranked), 4),
        "top1_mean_out_of_kb": round(statistics.mean(r["top1_score"] for r in ook), 4),
    }
    if cfg["judge"]:
        judged_rows = {r["id"]: JudgeResult.model_validate(r["judge"]) for r in out if "judge" in r}
        non_refused = [r for r in out if "judge" in r and not r["refused"]]
        m |= {
            "correctness_mean": (
                round(
                    statistics.mean(r.correctness for r in judged_rows.values()) / 2,
                    3,
                )
                if judged_rows
                else None
            ),
            "faithfulness_yes_rate": (
                round(
                    sum(r.faithfulness == "yes" for r in judged_rows.values()) / len(judged_rows),
                    3,
                )
                if judged_rows
                else None
            ),
            "citation_correct_rate": (
                round(
                    sum(r["judge"]["citation_correct"] for r in non_refused) / len(non_refused),
                    3,
                )
                if non_refused
                else None
            ),
            "cost_total": round(m["cost_total"] + sum(r.get("judge_cost", 0) for r in out), 6),
        }
        if gold:
            m["judge_agreement"] = agreement(judged_rows, gold)
    m["cost_per_question"] = round(m["cost_total"] / len(out), 6) if out else None
    if settings.score_threshold is not None and cfg.get("retrieval", "dense") == "dense":
        m["threshold_refusal_acc_out_of_kb"] = round(
            sum(r["top1_score"] < settings.score_threshold for r in ook) / len(ook),
            3,
        )
        m["threshold_false_refusal_in_kb"] = round(
            sum(r["top1_score"] < settings.score_threshold for r in ranked) / len(ranked),
            3,
        )
        eligible_thresholds = []
        for value in range(30, 81, 2):
            threshold = value / 100
            false_refusal = sum(r["top1_score"] < threshold for r in ranked) / len(ranked)
            if false_refusal <= 0.05:
                refusal_rate = sum(r["top1_score"] < threshold for r in ook) / len(ook)
                eligible_thresholds.append((refusal_rate, -false_refusal, threshold, false_refusal))
        if eligible_thresholds:
            refusal_rate, _, threshold, false_refusal = max(eligible_thresholds)
            m["threshold_scan_best"] = {
                "threshold": threshold,
                "refusal_acc_out_of_kb": round(refusal_rate, 3),
                "false_refusal_in_kb": round(false_refusal, 3),
            }
    return {
        "name": cfg["name"],
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "config": snapshot(cfg),
        "metrics": m,
        "rows": out,
    }


def build_md(report: dict) -> str:
    cfg, m = report["config"], report["metrics"]
    lines = [
        f"# RAG 基线报告 · {report['name']}",
        "",
        f"- 时间：{report['date']}",
        f"- git sha：`{cfg['git_sha']}`",
        "",
        "## 配置快照",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| dataset | {Path(cfg['dataset']).name}（{sum(1 for r in report['rows'])} 题）|",
        f"| collection | {cfg['collection']} |",
        f"| chunk_size | {cfg['chunk_size']} |",
        f"| overlap | {cfg['overlap']} |",
        f"| top_k | {cfg['top_k']} |",
        f"| retrieval | {cfg['retrieval']} |",
        f"| score_threshold | {cfg['score_threshold']} |",
        f"| embed_model | {cfg['embed_model']} |",
        f"| answer_prompt | {cfg['answer_prompt']} |",
        "",
        "## 指标",
        "",
        (
            "| hit@1 | hit@3 | hit@5 | MRR | 拒答正确率 | 库内误拒率 | "
            "检索P50 | 检索P95 | 回答P95 | 总成本 | 单题均成本 | top1均值(in_kb) | "
            "top1均值(out_of_kb) |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        (
            f"| {m['hit@1']} | {m['hit@3']} | {m['hit@5']} | {m['mrr']} "
            f"| {m['refusal_acc_out_of_kb']} | {m['false_refusal_in_kb']} "
            f"| {m['retrieve_p50_ms']}ms | {m['retrieve_p95_ms']}ms "
            f"| {m['answer_p95_ms']}ms | {m['cost_total']} "
            f"| {m['cost_per_question']} "
            f"| {m['top1_mean_in_kb']} | {m['top1_mean_out_of_kb']} |"
        ),
    ]
    if "correctness_mean" in m:
        lines += [
            "",
            "## 生成质量",
            "",
            "| 正确性均值（0–1） | 忠实度 yes 比例 | 引用正确率（非拒答） | Judge 一致率 |",
            "|---|---|---|---|",
            (
                f"| {m['correctness_mean']} | {m['faithfulness_yes_rate']} "
                f"| {m['citation_correct_rate']} "
                f"| {m.get('judge_agreement', {}).get('correctness', '未提供人工 gold')} |"
            ),
        ]
    if "threshold_refusal_acc_out_of_kb" in m:
        lines += [
            "",
            "## SCORE_THRESHOLD 校准（dense）",
            "",
            "| 阈值 | 库外自动拒答率 | 库内自动误拒率 |",
            "|---|---|---|",
            (
                f"| {cfg['score_threshold']} | {m['threshold_refusal_acc_out_of_kb']} "
                f"| {m['threshold_false_refusal_in_kb']} |"
            ),
            "",
            (
                f"分数扫描的最优候选为 {m['threshold_scan_best']['threshold']:.2f} "
                f"（库外拒答 {m['threshold_scan_best']['refusal_acc_out_of_kb']:.1%}，"
                f"库内误拒 {m['threshold_scan_best']['false_refusal_in_kb']:.1%}）；"
                "最终值会结合全量生成评测后的实际误拒率确定。"
            )
            if "threshold_scan_best" in m
            else "阈值按 top1_score < threshold 统计。",
        ]
    lines += [
        "",
        "## 最差 10 题（未命中或 rank > 5）",
        "",
        "| id | type | rank | top1_score | top3 |",
        "|---|---|---|---|---|",
    ]
    worst = [
        r
        for r in report["rows"]
        if r["type"] != "out_of_kb" and (r["rank"] is None or r["rank"] > 5)
    ][:10]
    for r in worst:
        top3 = "<br>".join(t.replace("|", "/") for t in r["top3"])
        lines.append(
            f"| {r['id']} | {r['type']} | {r['rank'] if r['rank'] else '-'} "
            f"| {r['top1_score']} | {top3} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG 检索指标 runner")
    ap.add_argument("--config", type=Path, default=None, help="YAML 配置（可选）")
    ap.add_argument("--name", default=None)
    ap.add_argument("--collection", default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--dataset", default=None)
    ap.add_argument("--with-answer", action="store_true", default=None)
    ap.add_argument("--judge", action="store_true", default=None)
    ap.add_argument("--retrieval", choices=["dense", "hybrid"], default=None)
    ap.add_argument("--stamp", default=None, help="报告文件名日期戳 YYYYMMDD（默认今天）")
    args = ap.parse_args()

    # 优先级：命令行 > YAML > settings
    cfg = {
        "name": "rag-baseline",
        "collection": "kb_default",
        "top_k": settings.top_k,
        "dataset": str(ROOT_DIR / "eval/datasets/kb_qa.jsonl"),
        "with_answer": False,
        "judge": False,
        "retrieval": settings.retrieval_mode,
        "stamp": time.strftime("%Y%m%d"),
    }
    if args.config:
        cfg |= yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    for key, val in (
        ("name", args.name),
        ("collection", args.collection),
        ("top_k", args.top_k),
        ("dataset", args.dataset),
        ("with_answer", args.with_answer),
        ("judge", args.judge),
        ("retrieval", args.retrieval),
        ("stamp", args.stamp),
    ):
        if val is not None:
            cfg[key] = val

    report = asyncio.run(run(cfg))

    stamp = cfg["stamp"]
    out_dir = ROOT_DIR / "eval/reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stamp}-{cfg['name']}.json"
    md_path = out_dir / f"{stamp}-{cfg['name']}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_md(report), encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print(f"→ JSON {json_path}")
    print(f"→ MD   {md_path}")


if __name__ == "__main__":
    main()
