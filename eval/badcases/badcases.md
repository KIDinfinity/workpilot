# Badcase 库

根因分类：未召回 / 召回排序靠后 / 分块切断 / 生成幻觉 / 引用错误 / 拒答失败 / 过度拒答 / 数据缺失
状态：open / fixing / fixed（附修复版本）/ wontfix

关联报告：`eval/reports/20261022-rag-v0.2.md`（v0.2）、`eval/reports/20261015-smoke-v0.1.md`（v0.1）
采集方式：`eval/runners/run_smoke.py`（v0.1）、`scripts/run_kb_smoke.py`（v0.2）+ 人工探针

| ID     | 版本      | 问题                                   | 现象                                    | 期望                     | 检索结果（top3 来源/分数）                         | 根因分类     | 修复思路              | 状态        |
| ------ | --------- | -------------------------------------- | --------------------------------------- | ------------------------ | ------------------------------------------------- | ------------ | --------------------- | ----------- |
| BC-001 | v0.1→v0.2 | WorkPilot 仓库的提交信息规范是什么？   | v0.1 编造并建议不存在的 CONTRIBUTING.md；v0.2 过度拒答 | 以 PROJECT_STANDARD §3 为准（Conventional Commits） | notes/da01-definition 0.63；notes/da01-definition 0.62；notes/da01-definition 0.61 | 召回排序靠后 | W5：hybrid / 标题加权 / query rewrite | open        |
| BC-002 | v0.1→v0.2 | WorkPilot 的 .env.example 里价格相关配置键有哪些？ | v0.1 拒答；v0.2 拒答                    | 列出 PRICE_CURRENCY / PRICE_INPUT_HIT_PER_M / PRICE_INPUT_MISS_PER_M / PRICE_OUTPUT_PER_M | notes/runbook 0.58；notes/da01-definition 0.55；notes/pain-pool 0.53 | 数据缺失     | W5：`.env.example` + 配置说明入库 | open        |
| BC-003 | v0.1→v0.2 | WorkPilot 项目里 React 组件文件和 hooks 分别怎么命名？ | v0.1 只给行业惯例；v0.2 过度拒答       | 组件 PascalCase.tsx、hooks useXxx.ts（PROJECT_STANDARD §2） | oss/react/your-first-component 0.67；oss/react/state-a-components-memory 0.66；oss/react/your-first-component 0.66 | 召回排序靠后 | W5：hybrid / 标题加权；语料补「规范」关键词 | open        |
| BC-004 | v0.1→v0.2 | 在 WorkPilot 里新增一个环境变量需要遵守哪些规则？ | v0.1 给通用注意；v0.2 已答对 §4 核心规则（部分修复） | 引用 PROJECT_STANDARD §4 的全部条目 | notes/PROJECT_STANDARD 0.63；oss/vite/env-and-mode 0.63；oss/vite/env-and-mode 0.62 | 生成幻觉（残留，见 BC-011） | W5：把 Vite 前端 env 与后端规范在 prompt 里区分 | fixed(v0.2)·部分 |
| BC-005 | v0.1→v0.2 | WorkPilot 支持哪些 LLM 供应商？       | v0.1 拒答；v0.2 拒答                    | deepseek（LLM_PROVIDER 可切换 doubao/ollama） | notes/da01-definition 0.59；notes/pain-pool 0.54；notes/runbook 0.53 | 数据缺失     | W5：`llm_providers.py` / `.env.example` 入库 | open        |
| BC-006 | v0.1→v0.2 | WorkPilot 的 API 有哪些端点？         | v0.1 给通用排查建议；v0.2 拒答          | 列出 /health、/v1/ask、/v1/kb/* 等端点 | notes/da01-definition 0.65；notes/da01-definition 0.63；notes/da01-definition 0.62 | 数据缺失     | W6：接入 /openapi.json 或写 API 清单文档入库 | open        |
| BC-007 | v0.1      | WorkPilot 的 v0.1 版本包含哪些能力？ | 拒答，建议查 CHANGELOG                    | v0.1 = 问答接口 + 冒烟评测 + badcase 库 | — | 数据缺失     | README 能力章节入库 | open        |
| BC-008 | v0.1      | WorkPilot 用的开源许可证是什么？     | 拒答，建议查 LICENSE / package.json      | 「内部项目，未声明开源许可证」 | — | 数据缺失     | 仓库根目录事实 + README 许可证说明 | open        |
| BC-009 | v0.1→v0.2 | 我们团队的 commit message 规范要求 scope 怎么写？（走 /v1/ask/stream） | v0.1 把 confidence/needs_more_context 字段名泄漏进正文 | 流式正文只保留人话 | — | 生成幻觉 / 引用错误（prompt 约束不足） | Day17 流式改用 qa_answer.v1 + done 事件带 citations | fixed(v0.2) |
| BC-010 | v0.2      | 提交信息里的 scope 和类型分别指什么？ | 检索到了 git-branching 仍过度拒答       | 类型=feat/fix/docs…，scope=模块范围；以 PROJECT_STANDARD 为准 | oss/fastapi/first-steps 0.60；team/git-branching 0.61；oss/fastapi/request-files 0.61 | 过度拒答     | W5：prompt 规则 3 收紧「有部分信息时应尽量回答」 | open        |
| BC-011 | v0.2      | 新增环境变量（后端）问题时混入 Vite 前端语义 | 答案正确引用 §4，却把 Vite「加载优先级/import.meta.env」拼进后端结论 | 只讲后端 pydantic-settings / .env 规则 | notes/PROJECT_STANDARD 0.63；oss/vite/env-and-mode 0.63；oss/vite/env-and-mode 0.62 | 生成幻觉 / 引用错误 | W5：区分前后端 env 的检索边界 | open        |
| BC-012 | v0.2      | 怎么在代码里读取环境变量？             | 只答 Vite 的 import.meta.env，漏掉后端 Settings(pydantic-settings) 规范 | 后端代码只经 Settings 读取（PROJECT_STANDARD §4） | oss/vite/env-and-mode 0.63；oss/vite/env-and-mode 0.63；oss/vite/env-and-mode 0.60 | 召回排序靠后 | W5：hybrid；「环境变量」歧义题加上下文消歧 | open        |

## 根因分布（v0.2）

- 召回排序靠后：BC-001、BC-003、BC-012（3）
- 数据缺失：BC-002、BC-005、BC-006、BC-007、BC-008（5）
- 生成幻觉 / 引用错误：BC-011（1）
- 过度拒答：BC-010（1）
- 修复：BC-009（fixed v0.2）、BC-004（部分修复）

## v0.1 → v0.2 私有知识题对比

v0.1 的 8 道私有题全部「拒答/编造」；v0.2 复测 6 道（BC-001~006）：

- 修复 1 道：BC-004 核心规则已能正确回答并引用 §4（残留的 Vite 混入见 BC-011）。
- 仍失败 5 道：2 道召回排序靠后（BC-001、BC-003），3 道数据缺失（BC-002、BC-005、BC-006——`.env.example`、`llm_providers.py`、`routes/` 尚未入库）。

## v0.3（2026-10-28）· Judge 分类与回归

报告：[`eval/reports/20261028-rag-v0.3.md`](../reports/20261028-rag-v0.3.md)；人工 gold：`eval/datasets/judge_gold.jsonl`。

首轮 14 条 correctness ≤ 1 的 badcase 中，过度拒答 7 条、关键要点遗漏 7 条。执行阈值和回答 prompt 修复后，50 题全量回归剩余 12 条：过度拒答 2 条、部分回答 / 要点遗漏 9 条、资料缺失或期望证据不匹配 1 条。忠实度与引用正确率均为 1.000；剩余错误主要不是无依据编造。

| 首轮根因 | 数量 / 题目 | 修复动作 | 回归结果 |
| --- | --- | --- | --- |
| 过度拒答 | 7：q003、q004、q005、q019、q025、q036、q038 | `SCORE_THRESHOLD` 从 0.60 调到 0.52；`qa_answer.v2` 鼓励在证据不足以完整作答时回答有依据的部分 | 库内误拒率 0.184 → 0.053；仍有 q003、q004 未召回 |
| 关键要点遗漏 | 7：q012、q018、q020、q022、q028、q035、q046 | `qa_answer.v2` 明确要求逐项覆盖问题要求、保留资料中的条件和示例 | correctness_mean 0.790 → 0.850；q022、q028 改善，仍有部分回答遗漏 |

阈值扫描的数学最优候选是 0.60（自动拒答库外 12/12、库内误拒 1/38），但全量问答测得库内误拒 0.184，因此最终采用 0.52（阈值自动误拒 0/38；最终生成拒答仍为 1.000）。这里区分「阈值自动拒答率」和「生成端实际拒答率」。

### v0.3 当前未解决项

| 题目 | 根因 | 现象 / 后续动作 | 状态 |
| --- | --- | --- | --- |
| q003、q004 | 未召回 | 对照 `notes/PROJECT_STANDARD.md` 的入库内容与 query top10；修复后回归 | open |
| q011、q012、q018、q019、q020、q025、q035、q046、q047 | 部分回答 / 要点遗漏 | 检查上下文是否含完整要点；仅基于证据改进 answer prompt，再做全量回归 | open |
| q036 | 数据缺失 / 期望证据不匹配 | 期望答案要求的压缩与 Rolldown 配置未由当前检索片段充分支持；先核对语料版本与题目来源 | open |

本轮修复后通过的评测题：q005、q022、q028、q038（`fixed(v0.3)`）。
