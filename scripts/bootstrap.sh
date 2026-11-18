#!/usr/bin/env bash
# 新机器 / 新 clone 后执行一次：准备 .env 并检查依赖工具
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  echo "[skip] .env 已存在"
else
  cp .env.example .env
  echo "[ok]   已从 .env.example 生成 .env —— 请填写其中的密钥"
fi

missing=0
check() {   # check <命令> <安装提示>
  if command -v "$1" >/dev/null 2>&1; then
    printf '[ok]   %-6s %s\n' "$1" "$("$1" --version 2>&1 | head -n1)"
  else
    printf '[miss] %-6s 安装：%s\n' "$1" "$2"
    missing=1
  fi
}
check docker "brew install --cask docker（并启动 Docker Desktop）"
check uv     "brew install uv"
check node   "brew install node"
check pnpm   "brew install pnpm"

if docker info >/dev/null 2>&1; then echo "[ok]   docker daemon 运行中"; else echo "[warn] docker daemon 未运行：打开 Docker Desktop"; fi
[[ $missing -eq 0 ]] && echo "环境就绪" || echo "有工具缺失，按上面提示安装后重跑 make bootstrap"
