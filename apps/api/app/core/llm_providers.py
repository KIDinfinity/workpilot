"""LLM 供应商预设（唯一的供应商配置来源）。

在 .env 里改 `LLM_PROVIDER=deepseek|doubao|ollama` 即可切换，业务代码零改动。
新增供应商 = 这里加一段 + Settings 里加一个对应的 *_api_key 字段。
所有供应商都走 OpenAI 兼容协议：POST {base_url}/chat/completions
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMProvider:
    base_url: str
    model: str
    api_key: str = ""  # 少数本地服务要求非空占位串
    extra_body: dict[str, Any] = field(default_factory=dict)  # 随手请求体一起发给上游
    note: str = ""


PROVIDERS: dict[str, LLMProvider] = {
    "deepseek": LLMProvider(
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        note="文档 https://api-docs.deepseek.com/",
    ),
    "doubao": LLMProvider(
        # 火山方舟 Ark 的 OpenAI 兼容入口（结尾不带 /v1）
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        # 本账号实测可用；查全部：client.models.list() 或控制台的推理接入点 ID（ep-xxxxxxxx）
        model="doubao-seed-2-1-pro-260915",
        # seed-2-x 系列默认「边想边答」，实测同一问题 26–43s，会撞超时；关掉后约 2.6s
        # 想看思考过程就删掉这一行（或改成 {"thinking": {"type": "enabled"}}）
        extra_body={"thinking": {"type": "disabled"}},
        note="不在账号可用列表里的模型会返回 404 InvalidEndpointOrModel.NotFound",
    ),
    "ollama": LLMProvider(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b",
        api_key="ollama",  # Ollama 不校验，但不能为空
        note="本地模型，Day09 安装后可用",
    ),
}
