# 项目规范

## §1 目录规范

| 路径 | 做什么 | 放什么 | 不放什么 |
| --- | --- | --- | --- |
| `README.md` | 项目门面 | 定位、快速开始、常用命令、架构图 | 长篇设计（→ `docs/`） |
| `PROJECT_STANDARD.md` | 本规范 | 目录 / 命名 / 提交 / 配置规则 | 业务说明 |
| `Makefile` | 统一命令入口 | 各 target 一两行调用 | 复杂逻辑（> 3 行 → `scripts/`） |
| `.env.example` | 配置清单 | 全部键 + 注释 + 安全默认值 | 任何真实密钥 |
| `.gitignore` / `.editorconfig` | 忽略规则 / 格式统一 | `.env*`、`data/`、`eval/runs/`；缩进 / 换行 / 编码 | 需提交的样例与报告 |
| `.github/copilot-instructions.md` | 强制本规范生效 | 指向本文件的最高优先级规则 + 速查 | 与规范重复的长篇说明 |
| `.github/instructions/*.instructions.md` | 按 `applyTo` 自动注入规范 | `project-standard.instructions.md`（`applyTo: "**"`） | 业务逻辑 |
| `AGENTS.md` | 跨工具代理入口 | 一句话规则 + 指向本文件 | 详细设计 |
| `apps/` | 可运行应用 | 每子目录一个可独立启动的 app，各自带 `tests/` | 实验脚本、笔记 |
| `apps/api/` | 后端 | `pyproject.toml`、`uv.lock`、`app/`、`tests/` | 前端代码、数据文件 |
| `apps/web/` | 前端 | `package.json`、`src/`、测试 | 后端逻辑、密钥 |
| `prompts/` | 版本化提示词 | `<name>.v<N>.md` | 代码里再复制一份 prompt |
| `eval/datasets/` | 评测集 | `*.jsonl`（公开 / 脱敏） | 机密数据 |
| `eval/runners/` | 评测脚本 | `run_*.py` | 业务代码 |
| `eval/reports/` | 评测报告（提交） | `YYYYMMDD-<name>.md` | 原始运行明细（→ `eval/runs/` 忽略） |
| `eval/badcases/` | 坏例库 | `badcases.md` | — |
| `data/` | 本地数据（忽略） | 语料、SQLite、导出文件 | 任何需要提交的东西 |
| `data/sample/` | 公开样例（提交） | ≤ 1MB 的可公开小样本 | 公司数据 |
| `deploy/` | 部署编排 | `docker-compose*.yml`、`Caddyfile` | 应用源码 |
| `deploy/scripts/` | 运维脚本 | `backup.sh`、`restore.sh`、`healthcheck.sh` | 开发辅助脚本 |
| `scripts/` | 开发辅助 | `bootstrap.sh`、`ingest.sh`、`chat.py` | 运维脚本、正式业务逻辑 |
| `docs/architecture.md` · `runbook.md` · `api.md` | 架构 / 运维手册 / 接口 | mermaid 图、操作步骤、端点示例 | — |
| `docs/adr/` | 架构决策 | `NNNN-kebab-title.md` | 会议纪要 |
| `docs/product/` · `docs/portfolio/` | 产品文档 / 求职写作 | 定位、场景、路线 / 项目复盘 | 实现细节 |
| `.gitea/workflows/` | CI | `ci.yml`（语法兼容 GitHub Actions） | 部署密钥 |

## §2 命名规范

| 类别 | 规则 | 示例 |
| --- | --- | --- |
| Python 模块 / 函数 / 变量 | `snake_case` | `load_config` |
| Python 类 | `PascalCase` | `Settings` |
| Python 常量 | `UPPER_SNAKE` | `MAX_RETRY` |
| React 组件文件与组件名 | `PascalCase.tsx` | `ChatPanel.tsx` |
| React hooks | `useXxx.ts` | `useChat.ts` |
| 其余 TS 文件 | `camelCase.ts` | `formatDate.ts` |
| 文档 | `kebab-case.md` | `api-design.md` |
| 约定大写文件 | 大写（例外） | `README.md` |
| prompt | `<name>.v<N>.md` | `qa_answer.v1.md` |
| ADR | `NNNN-kebab-title.md` | `0001-llm-provider.md` |
| 环境变量 | `UPPER_SNAKE`，按前缀分组 | `LLM_` / `EMBEDDING_` / `MINIO_` |
| 分支 | `feat/<短描述>` | `feat/rag-eval` |

## §3 分支与提交

- `main` 永远可运行。
- ≤ 1 天的改动可直接提交 `main`。
- 跨天 / 实验性改动用 `feat/xxx`，完成后合并并删分支。
- 提交遵循 Conventional Commits。

```text
feat(api): add /health endpoint
fix(llm): retry on timeout and 5xx responses
docs(adr): add 0001-llm-provider
test(rag): add hit@k unit tests
chore(deploy): pin qdrant image version
```

## §4 环境变量

- `.env` 永不提交。
- `.env.example` 列出全部键，每键一行注释并标 `[必填]` / `[可选]` / `[必填·密钥]`，密钥值留空。
- 新增键与使用它的代码同一个提交。
- 代码只通过 `Settings`（pydantic-settings）读取，不散落 `os.getenv`。
- 密钥轮换：疑似泄漏或每 90 天 → 平台生成新 key → 改 `.env` → 重启 → 验证 → 撤销旧 key。
- 误提交密钥一律视为已泄漏，立即轮换（改写 Git 历史不够）。

## §5 版本号与 tag

| 项 | 规则 |
| --- | --- |
| 版本方案 | SemVer |
| 0.x 阶段 | `v0.MINOR.0` 对应蓝图版本里程碑（v0.1 → `v0.1.0`），修复递增 PATCH |
| 打 tag | `git tag -a v0.1.0 -m "v0.1: ..."` + `git push origin v0.1.0` |
| 时机 | 只在 `main` 且 `make test` 通过后打 |
| 约束 | 已推送的 tag 不移动、不删除 |

## §6 Makefile 统一入口

| target | 说明 |
| --- | --- |
| `help` | 默认目标，自动列出 |
| `bootstrap` | 初始化环境 |
| `dev` | 本地开发启动 |
| `test` | 运行测试 |
| `lint` | 代码检查 |
| `up` | 启动服务 |
| `down` | 停止服务 |
| `logs` | 查看日志 |
| `eval` | 运行评测 |
| `backup` | 备份数据 |

每个 target 带 `## 说明`；任何人 clone 后只需记住 `make help`。

## §7 README 必含章节

1. 一句话定位
2. 功能
3. 架构
4. 快速开始
5. 目录
6. 常用命令
7. 配置
8. 评测
9. 部署
10. 路线图

## §8 ADR 模板

```markdown
# NNNN. 标题

- 状态：提议 | 已采纳 | 已废弃 | 被 NNNN 取代
- 日期：YYYY-MM-DD

## 背景（要解决什么问题，有什么约束）

## 决策（选了什么）

## 备选方案（列出并说明放弃理由）

## 后果（好处 / 代价 / 后续动作）
```

## §9 数据合规

- 公司机密代码 / 文档 / 工单不进入外部 LLM API。
- 语料只用自己笔记、公开开源文档、手工脱敏样例。
- 公司内真实使用需先获许可并用公司设施 + 本地模型。
- 主业时间不开发本项目。
- 公开仓库 / Demo 发布前做敏感信息检查。
