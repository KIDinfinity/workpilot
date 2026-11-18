---
id: task_breakdown
version: 1
model: deepseek-chat
changelog:
  - "v1 2026-10-12: 初版，用于 SP-B 需求拆解预演"
---

请把下面的需求拆成一组可独立执行的任务，并只输出一个 json 对象。

需求：{requirement}
技术栈：{stack}

要求：

1. 拆成 3–10 个任务，每个任务必须能被单独验收。
2. type 只能是 frontend、backend、test、doc 四个值之一。
3. estimate_hours 取 0.5–16 之间的数（含 0.5 与 16），只写数字。
4. acceptance 写「怎么算做完」，要可验证（有命令、有界面行为或有明确输出）。
5. 不确定的地方按常规工程做法给出合理假设，不要反问我，不要编造不存在的内部系统。
