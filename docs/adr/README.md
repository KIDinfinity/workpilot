# docs/adr

架构决策记录：NNNN-kebab-title.md，模板见 [0000-template.md](0000-template.md)。一篇一个决策，记录当时约束与放弃方案。

| ADR | 决策 | 状态 |
| --- | --- | --- |
| [0001](0001-llm-gateway.md) | LLM 供应商与网关：DeepSeek 默认 + 自建 OpenAI 兼容网关 | 已采纳 |
| [0002](0002-qdrant.md) | 向量库选 Qdrant（单容器 / payload 过滤 / 快照） | 已采纳 |
| [0003](0003-chunking-retrieval.md) | 分块与检索参数（600 / 100 / dense / top_k 5 / 0.52） | 已采纳 |
| [0004](0004-handwritten-rag.md) | RAG v1 手写，不用 LangChain | 已采纳 |
| [0005](0005-compose-caddy.md) | 单机 Compose + Caddy 反代（IP + HTTP，域名/TLS 后续） | 已采纳 |
