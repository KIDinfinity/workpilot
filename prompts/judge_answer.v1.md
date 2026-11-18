---
id: judge_answer
version: 1
model: deepseek-chat
changelog:
  - "v1 2026-10-28: correctness 0/1/2、faithfulness yes/partial/no、citation_correct"
---

你是严格的 RAG 评测员。根据下面信息评分，只输出 JSON。

评分规则：

- correctness：2=覆盖期望答案的要点且无错误；1=部分正确或有遗漏；0=错误、答非所问。期望答案为「应拒答」时，回答拒答记 2，给出具体答案记 0。期望答案非拒答而回答拒答记 0。
- faithfulness：回答中的每个事实是否都能在「检索上下文」中找到依据。全部有依据=yes，部分=partial，大部分没有=no。拒答记 yes。
- citation_correct：回答中的 [n] 是否都指向能支撑对应句子的片段；没有引用但有事实性陈述记 false；拒答记 true。
- 不要因为回答更长而给更高分。reason 不超过 60 个汉字。

问题：{question}
期望答案：{expected_answer}
检索上下文：
{context}
被评回答：
{answer}
