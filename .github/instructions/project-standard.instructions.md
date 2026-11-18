---
description: "仓库规范强制生效 — 生成/修改任何文件前先读 PROJECT_STANDARD.md"
applyTo: "**"
---

在生成或修改任何文件前，必须先读取并遵守仓库根目录 `PROJECT_STANDARD.md` 的全部 9 节：

- §1 目录规范：文件放错目录视为错误；不确定时先查表，不要自创新目录。
- §2 命名规范：按语言/文档类型套用对应命名。
- §3 分支与提交：提交信息用 Conventional Commits。
- §4 环境变量：新增配置必须同步 `.env.example`，密钥一律留空；代码只用 `Settings` 读取。
- §5 版本号与 tag：只在 `main` + `make test` 通过后打附注 tag。
- §6 Makefile：新增命令走 Makefile target + `## 说明`。
- §7 README 章节齐全。
- §8 ADR 用 `docs/adr/NNNN-kebab-title.md` 模板。
- §9 数据合规：公司机密 / 未脱敏数据不得进入外部 LLM API。

输出中文、精简、表格优先。与标准冲突时以 `PROJECT_STANDARD.md` 为准并说明。
