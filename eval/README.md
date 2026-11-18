# eval

评测数据放在 `datasets/`，脚本放在 `runners/`，汇总报告放在 `reports/`，坏例放在 `badcases/`；逐题结果包含上下文，仅用于本地报告，不提交额外运行日志。

## RAG + LLM-judge

在仓库根目录运行：

```bash
make eval-rag ARGS="--with-answer --name pre-judge --stamp 20261028"
make eval-rag-judge ARGS="--stamp 20261028"
```

`judge_gold.jsonl` 必须由人工标注；Judge 的一致率只统计与 gold ID 匹配的样本。JSON 报告保存逐题答案、检索上下文和 judge 理由，Markdown 报告保存汇总指标与配置快照。
