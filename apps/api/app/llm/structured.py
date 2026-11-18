"""Structured Output：让模型返回「通过 Pydantic 校验的 JSON」。

四层保障（缺一不可）：
1. 请求带 `response_format={"type": "json_object"}`（JSON mode）——只保证是合法 JSON；
2. system prompt 注入 `model_json_schema()`，让模型知道字段名 / 类型 / 枚举；
3. `model_validate_json()` 一步完成解析 + 校验；
4. 校验失败：把 `e.errors()` 回灌给模型让它自己修，只重试 1 次（成本可控）。

仍然失败的，抛 `StructuredError`，由路由转成 502 —— 不把模型原文回给前端。
"""

import json

from pydantic import BaseModel, ValidationError

from app.llm.gateway import LLMGateway
from app.llm.schemas import ChatResult

# DeepSeek 的 JSON mode 要求 prompt 里出现小写 "json" 字样，所以下面必须保留 json 一词。
SYSTEM = (
    "你是 WorkPilot 的结构化输出模块。只输出一个 json 对象，不要 Markdown 代码块，不要解释。\n"
    "json 必须符合以下 JSON Schema：\n{schema}"
)

_REPAIR_HINT = "上面的 json 未通过校验，错误如下，请修正后只输出完整 json："


class StructuredError(Exception):
    """模型在 max_retries 次修正后仍未产出合法结构。"""


async def generate_structured[T: BaseModel](
    model_cls: type[T],
    messages: list[dict[str, str]],
    *,
    gw: LLMGateway,
    max_retries: int = 1,
    **extra: object,
) -> tuple[T, ChatResult]:
    """返回 (校验通过的对象, 最后一次的原始 ChatResult)。"""
    schema = json.dumps(model_cls.model_json_schema(), ensure_ascii=False)
    msgs = [{"role": "system", "content": SYSTEM.format(schema=schema)}, *messages]
    extra.setdefault("temperature", 0.2)  # 调用方可覆盖（W5 judge 传 temperature=0）
    extra.setdefault("max_tokens", 1500)  # 防截断；PLAN 建议 1500–2000
    last_err: Exception | None = None
    for _ in range(max_retries + 1):
        res = await gw.chat(msgs, response_format={"type": "json_object"}, **extra)
        try:
            return model_cls.model_validate_json(res.content), res
        except ValidationError as e:  # 空串 / 非法 JSON / 字段不合法 都进这里
            last_err = e
            msgs += [
                {"role": "assistant", "content": res.content or "(空)"},
                {
                    "role": "user",
                    "content": _REPAIR_HINT
                    + "\n"
                    + json.dumps(e.errors(include_url=False), ensure_ascii=False, default=str),
                },
            ]
    raise StructuredError(f"{model_cls.__name__} 校验失败：{last_err}")
