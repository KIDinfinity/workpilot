# 语料来源与许可登记（SOURCES）

> 记录 `data/corpus/` 中每类语料的来源、commit/日期、许可证与合规结论。
> 本文件与 `data/corpus/` 一起被 `.gitignore` 忽略；可提交副本见 `docs/product/corpus-sources.md`。

## 类别总览

| 类别 | 路径            | 来源                                                       | commit / 日期 | 许可        | 合规检查                                 |
| ---- | --------------- | ---------------------------------------------------------- | ------------- | ----------- | ---------------------------------------- |
| oss  | `oss/fastapi/`  | github.com/fastapi/fastapi `docs/zh/docs/tutorial`（子集） | e5fc7ef       | MIT         | 公开文档，仅挑选 12 篇                    |
| oss  | `oss/react/`    | github.com/reactjs/zh-hans.react.dev `src/content/learn`（子集） | cbd15b3  | CC BY 4.0   | 公开文档，保留署名，仅挑选 12 篇         |
| oss  | `oss/vite/`     | github.com/vitejs/docs-cn `guide`（子集）                  | dc1f526       | MIT         | 公开文档，仅挑选 10 篇                    |
| notes | `notes/*.md`    | WorkPilot 自有文档 + 自写笔记                              | 2026-10-19    | 自有        | 已 grep，无公司名/人名/内部域名/内网 IP |
| team | `team/*.md`     | 本人重写的通用团队规范样例                                 | 2026-10-19    | 自有        | 已 grep，无公司信息，去敏               |
| pdf   | `pdf/*.pdf`     | 由 `team/frontend-code-review.md` 导出的 PDF 样本          | 2026-10-19    | 自有        | 无敏感信息                             |
| html  | `html/*.html`   | 公开文档网页（保存用于测 loader）                          | 2026-10-19    | 同来源      | 公开文档                               |

## oss 明细

| 路径                              | 来源仓库                                       | commit | 许可 |
| --------------------------------- | ---------------------------------------------- | ------ | ---- |
| `oss/fastapi/`（12 篇）           | github.com/fastapi/fastapi `docs/zh/docs/tutorial` | e5fc7ef | MIT |
| `oss/react/`（12 篇）             | github.com/reactjs/zh-hans.react.dev `src/content/learn` | cbd15b3 | CC BY 4.0 |
| `oss/vite/`（10 篇）              | github.com/vitejs/docs-cn `guide`             | dc1f526 | MIT |

## html 明细

| 文件                        | 来源 URL                                          | 日期       |
| --------------------------- | ------------------------------------------------- | ---------- |
| `html/fastapi-first-steps.html` | https://fastapi.tiangolo.com/zh/tutorial/first-steps/ | 2026-10-19 |
| `html/vite-guide.html`          | https://cn.vite.dev/guide/                        | 2026-10-19 |

## 合规检查结果（2026-10-19 执行）

- 敏感模式 grep（`password|secret|api[_-]?key|token=|内网 IP`）在 `data/corpus/`：
  - 命中均为**误报/公开文档正常内容**，无真实密钥：
    - `oss/fastapi/response-model.md`：公开文档示例代码中的 `password` 字段说明。
    - `oss/react/keeping-components-pure.md`：React 文档标题「局部 mutation：组件的小秘密」中的「秘密」。
    - `html/*.html`：SVG path 坐标中的 `10.xxx` 数字片段，非 IP。
  - 无 `api_key`、无 `token=`、无真实内网 IP、无真实密码。
- 公司/人名/域名 grep：`notes/pain-pool.md`、`notes/da01-definition.md` 中「公司/同事」均为**抽象化描述**（已按规则去公司名/人名/产品名），非真实公司信息。
- `team/*.md` 为本人重写样例，无复制粘贴的公司原文。

## 已排除的文件及原因

- 无（本次未发现需排除的文件）。

## 许可说明

- FastAPI（MIT）、Vite（MIT）允许复制与再分发，需保留版权与许可声明（原文自带）。
- React 中文文档（CC BY 4.0）需保留署名；`data/sample/` 中保留原文件头部的来源与许可说明。
