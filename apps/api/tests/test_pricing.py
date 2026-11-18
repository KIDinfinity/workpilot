from app.core.config import get_settings
from app.llm.pricing import calc_cost, estimate_tokens
from app.llm.schemas import Usage


def test_calc_cost_with_configured_prices(monkeypatch):
    # 假单价：命中 1 / 未命中 2 / 输出 3（元每百万）
    s = get_settings()
    monkeypatch.setattr(s, "price_input_hit_per_m", 1.0)
    monkeypatch.setattr(s, "price_input_miss_per_m", 2.0)
    monkeypatch.setattr(s, "price_output_per_m", 3.0)
    u = Usage(prompt_tokens=1000, cache_hit_tokens=400, completion_tokens=500)
    # 命中 400×1 + 未命中 600×2 + 输出 500×3 = 400+1200+1500 = 3100 /1e6
    assert calc_cost(u) == 0.0031


def test_calc_cost_clamps_negative_miss(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "price_input_hit_per_m", 1.0)
    monkeypatch.setattr(s, "price_input_miss_per_m", 2.0)
    monkeypatch.setattr(s, "price_output_per_m", 3.0)
    # cache_hit 超过 prompt，未命中按 0 计，不为负：150×1/1e6 = 0.00015
    u = Usage(prompt_tokens=100, cache_hit_tokens=150, completion_tokens=0)
    assert calc_cost(u) == 0.00015


def test_calc_cost_returns_none_when_unconfigured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "price_input_hit_per_m", None)
    monkeypatch.setattr(s, "price_input_miss_per_m", 1.0)
    monkeypatch.setattr(s, "price_output_per_m", 3.0)
    assert calc_cost(Usage(prompt_tokens=10, completion_tokens=10)) is None


def test_estimate_tokens_positive():
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("中文") > 0
    assert estimate_tokens("") >= 1
