# Copilot 仓库指令

## 强制规则（最高优先级）

生成、修改、移动或评审任何代码 / 脚本 / 文件之前，必须先读取仓库根目录的 `PROJECT_STANDARD.md`，并严格遵守其中的 §1–§9。

- 不确定文件该放哪 → 查 `PROJECT_STANDARD.md` §1 目录规范，不要新建目录。
- 命名 → §2；提交信息 → §3（Conventional Commits）；环境变量 → §4。
- 新增代码若需要配置项 → 同步更新 `.env.example`（同一提交，§4）。
- 任何疑似密钥 / 真实 token / 公司数据 → 拒绝并提示（§4、§9）。
- 不要绕过 `Makefile` 新增散乱命令入口（§6）。

## 最小速查

- 目录：根 6（`README` / `PROJECT_STANDARD` / `Makefile` / `.env.example` / `.gitignore` / `.editorconfig`）、`apps/`、`prompts/`、`eval/{datasets,runners,reports,badcases}`、`data/`(忽略) + `data/sample/`(提交)、`deploy/{,scripts/}`、`scripts/`、`docs/{adr,product,portfolio}`、`.gitea/workflows/`。
- 命名：Python `snake_case` / 类 `PascalCase` / 常量 `UPPER_SNAKE`；React 组件 `PascalCase.tsx`、hooks `useXxx.ts`、其余 `camelCase.ts`；文档 `kebab-case.md`；prompt `<name>.v<N>.md`；ADR `NNNN-kebab-title.md`。
- 提交：`feat(scope): ...` / `fix(scope): ...` / `docs(adr): ...` / `test(scope): ...` / `chore(deploy): ...`。
- 配置：只经 pydantic-settings `Settings` 读取，禁止散落 `os.getenv`。

## 回答要求

- 中文，精简，表格优先，不加多余内容。
- 与 `PROJECT_STANDARD.md` 冲突时，以标准文件为准并指出冲突。
