#!/usr/bin/env bash
# 跑一组受控实验：每个 YAML 变体 → 独立 collection 入库 → 检索评测报告
# 用法（仓库根目录）：scripts/run_experiments.sh eval/configs/c300_o0.yaml ...
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIGS=()
for cfg in "$@"; do
  case "$cfg" in
    /*) CONFIGS+=("$cfg") ;;
    *) CONFIGS+=("$ROOT/$cfg") ;;
  esac
done

cd "$ROOT/apps/api"
for cfg in "${CONFIGS[@]}"; do
  echo "=== $cfg ==="
  uv run python -m app.rag.ingest --path ../../data/corpus --config "$cfg" | tail -2
  PYTHONPATH=. uv run python ../../eval/runners/run_rag_eval.py --config "$cfg"
done
