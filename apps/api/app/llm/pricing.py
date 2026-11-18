from app.core.config import get_settings
from app.llm.schemas import Usage


def calc_cost(u: Usage) -> float | None:
    s = get_settings()
    if None in (s.price_input_hit_per_m, s.price_input_miss_per_m, s.price_output_per_m):
        return None                                  # 未配置价格：不猜
    miss = max(u.prompt_tokens - u.cache_hit_tokens, 0)
    total = (u.cache_hit_tokens * s.price_input_hit_per_m
             + miss * s.price_input_miss_per_m
             + u.completion_tokens * s.price_output_per_m)
    return round(total / 1_000_000, 6)


def estimate_tokens(text: str) -> int:
    """无 usage 时的粗估：以 DeepSeek 文档的中英文换算比例为准，这里用保守值。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return int(cjk * 0.6 + (len(text) - cjk) * 0.3) + 1
