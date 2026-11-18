# 0001. LLM 供应商与网关：DeepSeek 默认 + 自建 OpenAI 兼容网关

- 状态：已采纳
- 日期：2026-10-12（W2）

## 背景（要解决什么问题，有什么约束）

v0.1 需要一条统一的 LLM 调用入口，但有几个明确约束：

- 不能把供应商 SDK 的细节散落在业务代码里，否则将来换供应商要到处改。
- 需要统一的**超时 / 重试 / 错误码映射**，上游各自报错格式不一致。
- 需要**计量**：token 用量与成本要能按 `PRICE_*` 计价并回写响应。
- 预算与工期都很紧，不能引入一个需要单独运维的重服务。
- 供应商可能变化（DeepSeek → Qwen / doubao / Ollama 本地），切换成本要低。

## 决策（选了什么）

**默认供应商 DeepSeek（`LLM_PROVIDER=deepseek`），自建一个 OpenAI 兼容协议的网关层**，
统一封装超时（`LLM_TIMEOUT_S=30`）、重试（`LLM_MAX_ATTEMPTS=3`）、错误码映射、
token 用量与成本核算。供应商预设集中在 `apps/api/app/core/llm_providers.py`，
切供应商只改 `LLM_PROVIDER` 一个变量；密钥按供应商分开存（`DEEPSEEK_API_KEY` /
`DOUBAO_API_KEY`），切换时不互相覆盖。

- 网关只依赖 OpenAI 兼容协议（`/chat/completions`），不依赖任何供应商专有 SDK。
- Qwen / doubao / Ollama 作为可配置的 fallback 预设，而非代码分支。
- 成本：`PRICE_*`（每百万 token 价格）未配置时 `cost=None`，不猜测。

## 备选方案（列出并说明放弃理由）

- **直接调供应商 SDK（openai / deepseek 各自）**：最简单，但无法统一计量与切换，
  换供应商要改业务代码；错误码也各自为政。放弃。
- **LiteLLM**：功能全、支持几十家，但要额外跑一层服务、多一份运维与状态管理，
  超出 W2 需要的规模；且团队只有一个供应商时收益有限。放弃。
- **Qwen / doubao 作为默认**：当时 DeepSeek 中文质量 / 价格 / 稳定性更适合当前
  RAG 问答场景，故作为 fallback 而非默认。

## 后果（好处 / 代价 / 后续动作）

好处：

- 业务代码（`apps/api/app/llm/gateway.py`）只面向一个统一接口，供应商变化零侵入。
- 超时 / 重试 / 错误映射 / 计量收敛在一处，可单测（`test_llm_gateway.py`）。
- 成本按真实 `PRICE_*` 计价，评测报告里的成本数字可追溯。

代价：

- 自建网关只覆盖 OpenAI 兼容协议；供应商若改用非兼容协议需额外适配。
- 没有 LiteLLM 那种现成的多供应商路由 / 限流 / 缓存能力，后续需要再评估。

复审条件：

- 需要同时接 ≥ 3 家供应商、或需要跨供应商路由 / 限流 / 缓存时，重新评估 LiteLLM。
