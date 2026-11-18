#!/usr/bin/env bash
# scripts/seed_sample.sh — 批量上传 data/sample/*.md
# 本地：make seed   云端：BASE=https://域名 BASIC_AUTH=user:pass ./scripts/seed_sample.sh
set -euo pipefail
cd "$(dirname "$0")/.."   # 允许在任意目录执行
BASE="${BASE:-http://localhost:8080}"
count=0
for f in data/sample/*.md; do
  case "$(basename "$f")" in
    SOURCES.md|README.md) continue ;;   # 来源登记，不是知识库内容
  esac
  echo "upload $f"
  curl -sfS ${BASIC_AUTH:+-u "$BASIC_AUTH"} -F "file=@${f}" "$BASE/v1/kb/upload"; echo
  count=$((count + 1))
done
echo "uploaded $count files to $BASE"
