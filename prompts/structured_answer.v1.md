---
id: structured_answer
version: 1
model: deepseek-chat
changelog:
  - "v1 2026-10-12: 初版，用于文档助手 v0 的结构化回答"
---

请回答下面的研发技术问题，并只输出一个 json 对象。

问题：{question}
可参考的上下文（可能为空）：{context}

要求：

1. answer 用中文，≤ 300 字，先给结论再给理由。
2. key_points 列 2–5 条要点。
3. 你不确定或问题依赖特定团队/公司内部信息时，confidence 设为 low，needs_more_context 设为 true，不要编造。
