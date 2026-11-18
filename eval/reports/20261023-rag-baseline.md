# RAG 基线报告 · rag-baseline

- 时间：2026-10-23 19:49
- git sha：`f10c970`

## 配置快照

| 项 | 值 |
|---|---|
| dataset | kb_qa.jsonl（50 题）|
| collection | kb_default |
| chunk_size | 600 |
| overlap | 100 |
| top_k | 5 |
| retrieval | dense |
| embed_model | bge-m3 |
| answer_prompt | qa_answer.v1 |

## 指标

| hit@1 | hit@3 | hit@5 | MRR | 拒答正确率 | 库内误拒率 | 检索P50 | 检索P95 | 回答P95 | 总成本 | top1均值(in_kb) | top1均值(out_of_kb) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.737 | 0.789 | 0.921 | 0.789 | 1.0 | 0.132 | 79ms | 148ms | 2280ms | 0.040968 | 0.7026 | 0.5358 |

## 最差 10 题（未命中或 rank > 5）

| id | type | rank | top1_score | top3 |
|---|---|---|---|---|
| q003 | in_kb | - | 0.6098 | notes/da01-definition.md#DA-01 定义：WorkPilot（2026-10-14 · v1） > 4. W4 语料计划（目标 30–80 篇）<br>notes/da01-definition.md#DA-01 定义：WorkPilot（2026-10-14 · v1） > 4. W4 语料计划（目标 30–80 篇） > 合规检查清单（Day15 执行时逐项打勾）<br>notes/runbook.md#Runbook > 技术债 |
| q004 | in_kb | - | 0.6132 | oss/react/your-first-component.md#组件：UI 构成要素 {/*components-ui-building-blocks*/}<br>oss/react/your-first-component.md#组件：UI 构成要素 {/*components-ui-building-blocks*/}<br>oss/react/your-first-component.md#使用组件 {/*using-a-component*/} > 嵌套和组织组件 {/*nesting-and-organizing-components*/} > 万物皆组件 {/*components-all-the-way-down*/} |
| q025 | in_kb | - | 0.6709 | oss/react/passing-props-to-a-component.md#向组件传递 props {/*passing-props-to-a-component*/} > 步骤 2: 在子组件中读取 props {/*step-2-read-props-inside-the-child-component*/}<br>oss/react/keeping-components-pure.md#副作用：（不符合）预期的后果 {/*side-effects-unintended-consequences*/} > 使用严格模式检测不纯的计算 {/*detecting-impure-calculations-with-strict-mode*/}<br>oss/react/passing-props-to-a-component.md#Props 如何随时间变化 {/*how-props-change-over-time*/} |
