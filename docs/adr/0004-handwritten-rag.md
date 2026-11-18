# 0004. RAG v1 不使用 LangChain，手写检索与生成链路

- 状态：已采纳
- 日期：2026-10-19（W4）

## 背景（要解决什么问题，有什么约束）

P1 需要一个**可解释、可评测、可调参**的 RAG：loaders → chunking → embedding →
retrieve → answer 每一步都要能被单独度量（hit@5 是检索、忠实度是生成），作者也要在
面试中讲清每一步原理。约束：

- 每天 1–2 小时，调试框架抽象层的时间成本高。
- 评测要定位「是哪一步出错」，框架的黑盒抽象会让定位变难。
- 依赖要少、镜像要小，便于单机 Docker 部署。

## 决策（选了什么）

**loaders / chunking / embedding / retrieve / answer 全部手写（约 800 行，
`apps/api/app/rag/`），只依赖 `openai` SDK 与 `qdrant-client`。** 不引入
LangChain / LlamaIndex / Haystack。每个环节是独立模块，可单测、可在评测报告中
单独度量。

- loaders：md / pdf / html / txt 各自一个文件（`apps/api/app/rag/loaders/`）。
- chunking：标题感知分块（600/100，见 ADR 0003）。
- retrieve：dense + hybrid（命名向量 + RRF），阈值拒答。
- answer：版本化 prompt（`qa_answer.vN`）+ 引用 + 拒答分支。

## 备选方案（列出并说明放弃理由）

- **LangChain / LlamaIndex**：上手快、生态全；但抽象层深，评测时难以定位是哪一步
  出错，版本变动频繁，且为了几个 loader / retriever 引入整套依赖不划算。
- **Haystack**：pipeline 清晰；但同样引入一套框架概念，且单机小规模场景收益有限。

## 后果（好处 / 代价 / 后续动作）

正面：

- 每个环节可单测，评测报告可单独度量（hit@5 vs 生成质量），排障能定位到具体步骤。
- 依赖少、镜像小，部署与镜像构建都快。
- 面试时能逐行讲清 RAG 每一步，而不仅是「调了某个框架」。

负面：

- loader 种类少（当前 md / pdf / html / txt），新增格式要自己写。
- 需要自己维护分块 / 检索 / 拒答的边界情况。

复审条件：

- 需要支持 > 10 种数据源，或团队协作需要统一框架时重新评估；
  W11 的 Agent 层计划引入 LangGraph（另记 ADR），与本决定不冲突。
