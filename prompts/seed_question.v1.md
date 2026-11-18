---
id: seed_question
version: 1
model: deepseek-chat
changelog:
  - "v1 2026-10-26: 从知识库片段生成候选评测题（llm_seed），仅输出 json，answerable=false 跳过"
---

下面是知识库中的一段资料。请站在「一个忙碌的工程师在工作中遇到问题」的角度，提出 1 个可以仅凭这段资料回答的问题。
要求：不要照抄资料中的句子和标题用词，用口语化的说法；不要问「这段资料讲了什么」；如果资料信息量太少，answerable 设为 false。
输出 json：question、expected_answer（≤ 80 字）、answerable。

文档：{title}
章节：{section}
资料：
{text}
