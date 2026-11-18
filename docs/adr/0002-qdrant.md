# 0002. 向量库：选择 Qdrant（单容器、payload 过滤、hybrid、快照）

- 状态：已采纳
- 日期：2026-10-17（W4）

## 背景（要解决什么问题，有什么约束）

v0.2 做 RAG MVP，需要一个向量库承载 bge-m3 的 1024 维向量，并满足：

- 检索要带 **payload 过滤**（按 `doc_id` / `title` / `section` 过滤，用于引用溯源）。
- 希望未来能做 **hybrid 检索**（dense + sparse，W5 已用命名向量验证）。
- 需要**快照备份 / 恢复**能力（W7 备份脚本依赖 Qdrant collection snapshot）。
- 单机部署，预算与运维都要轻；作者每天 1–2 小时，不能扛一个重组件。

## 决策（选了什么）

**选 Qdrant（`qdrant/qdrant`），单容器部署**：一个 collection 承载向量 + payload，
支持命名向量（dense + sparse BM25）、payload 过滤、snapshot 快照，HTTP API
（`6333`）简单，`docker compose` 里一个 service 即可跑起来。

- 检索用 `FusionQuery(RRF)` 支持 hybrid（代码保留，默认 dense，见 ADR 0003）。
- 备份用 collection snapshot API（`POST /collections/{c}/snapshots`）。

## 备选方案（列出并说明放弃理由）

- **pgvector（Postgres 扩展）**：业务库 W19 才引入 Postgres，W4 时没有 Postgres，
  为此先起一个 Postgres 只为向量，重且收益低；等 W19 有 Postgres 后可再复审。
- **Milvus**：功能强（大规模、多索引），但是分布式组件，单机部署重、运维成本高，
  远超当前 50 题 / 千级分块的规模。放弃。
- **Chroma**：上手最简单，但生产级能力（快照、payload 过滤、hybrid）较弱，
  不利于后续评测与备份。放弃。

## 后果（好处 / 代价 / 后续动作）

好处：

- 一个容器跑通向量 + payload + 快照，compose 里 `service_healthy` 即用。
- hybrid（命名向量 + RRF）与 snapshot 备份都开箱可用，W5 / W7 直接复用。
- payload 过滤让「按 doc_id 溯源引用」成为可能。

代价：

- Qdrant 是独立组件，需要单独健康检查与快照恢复流程（见 runbook 备份 / 恢复）。
- 快照恢复要求 Qdrant 版本兼容，升级时要核对 tag。

复审条件：

- W19 引入 Postgres 后，若业务与向量能同库托管，可重新评估 pgvector，
  以少一个独立组件。
