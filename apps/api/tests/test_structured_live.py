"""Step5 · 真实 LLM 的 5 输入通过率（需要 .env 密钥、产生费用）。

跑法：cd apps/api && uv run pytest -m live -s -q

统计口径：
- final      = 最终校验通过（允许 1 次错误回灌重试）
- first-try  = 第一次调用就通过（用计数包装器数实际 chat 次数，不额外发请求）

5 个输入覆盖：通用问题 / 团队内部问题 / 模糊问题 / 需求拆解 ×2。
"""

import pytest

from app.core.config import get_settings
from app.llm import structured
from app.llm.gateway import LLMGateway
from app.llm.prompts import load_prompt
from app.llm.schemas import StructuredAnswer, TaskBreakdown
from app.llm.structured import StructuredError

pytestmark = pytest.mark.live


def _shape(data) -> str:
    if isinstance(data, StructuredAnswer):
        return (
            f"confidence={data.confidence} need_ctx={data.needs_more_context} "
            f"points={len(data.key_points)} ans_len={len(data.answer)}"
        )
    return f"tasks={len(data.tasks)} types={sorted({t.type for t in data.tasks})}"


CASES = [
    (
        "answer-通用",
        StructuredAnswer,
        "structured_answer.v1",
        {
            "question": "Python 的 GIL 是什么？它对多线程 IO 密集型任务有什么影响？",
            "context": "（无）",
        },
    ),
    (
        "answer-团队内部",
        StructuredAnswer,
        "structured_answer.v1",
        {"question": "我们团队生产环境的 Grafana 面板放在哪个地址？", "context": "（无）"},
    ),
    (
        "answer-模糊",
        StructuredAnswer,
        "structured_answer.v1",
        {"question": "这个功能能不能再优化一下？", "context": "（无）"},
    ),
    (
        "breakdown-文档上传",
        TaskBreakdown,
        "task_breakdown.v1",
        {
            "requirement": "给知识库页面加文档上传：支持 md/pdf，显示处理状态，失败可重试",
            "stack": "React + FastAPI",
        },
    ),
    (
        "breakdown-JWT",
        TaskBreakdown,
        "task_breakdown.v1",
        {
            "requirement": "为 API 增加 JWT 鉴权：登录发 token、受保护路由校验、token 过期返回 401",
            "stack": "FastAPI + SQLite",
        },
    ),
]


class CountingGW:
    """透明包装真实 Gateway，只数调用次数——用来区分「首次即通过」与「重试后通过」。"""

    def __init__(self, inner: LLMGateway):
        self.inner, self.count = inner, 0

    async def chat(self, messages, **kw):
        self.count += 1
        return await self.inner.chat(messages, **kw)


async def test_structured_pass_rate_5_cases():
    real = LLMGateway(get_settings())
    gw = CountingGW(real)
    ok = first = 0
    rows = []
    try:
        for name, model_cls, prompt_name, values in CASES:
            p = load_prompt(prompt_name)
            text = p.render(**values)
            before = gw.count
            try:
                data, res = await structured.generate_structured(
                    model_cls, [{"role": "user", "content": text}], gw=gw
                )
            except StructuredError as e:
                rows.append((name, "FAIL", gw.count - before, 0, 0, str(e)[:80]))
                continue
            one_shot = gw.count - before == 1
            ok += 1
            first += one_shot
            rows.append(
                (
                    name,
                    "OK",
                    gw.count - before,
                    res.usage.prompt_tokens,
                    res.usage.completion_tokens,
                    _shape(data),
                )
            )
            if isinstance(data, StructuredAnswer) and name == "answer-团队内部":
                # prompt 要求：问了答案不在模型知识里的内部信息时必须 low + 需要更多上下文
                assert data.confidence == "low" and data.needs_more_context, (
                    "内部信息问题应返回 low / needs_more_context=true，实际："
                    f"{data.confidence} / {data.needs_more_context}"
                )
    finally:
        await real.aclose()

    print("\n=== structured output 5 输入明细 ===")
    for name, status, calls, pt, ct, extra in rows:
        print(f"{name:16} {status:4} calls={calls} tokens={pt}+{ct}  {extra}")
    print(f"structured pass rate: {ok}/5, first-try: {first}/5")
    assert ok >= 4, f"通过率不足：{ok}/5"
