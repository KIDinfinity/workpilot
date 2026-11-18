import pytest

from app.llm import prompts
from app.llm.prompts import Prompt, load_prompt


class _SettingsStub:
    def __init__(self, prompts_dir):
        self.prompts_dir = prompts_dir


def test_load_structured_answer_v1():
    p = load_prompt("structured_answer.v1")
    assert p.ref == "structured_answer.v1"
    assert p.id == "structured_answer"
    assert p.version == "1"
    assert p.model  # front matter 必须写明默认模型
    assert "{question}" in p.body and "{context}" in p.body


def test_load_task_breakdown_v1():
    p = load_prompt("task_breakdown.v1")
    assert p.ref == "task_breakdown.v1"
    assert "{requirement}" in p.body and "{stack}" in p.body


def test_render_replaces_all_variables():
    out = load_prompt("structured_answer.v1").render(question="Q", context="C")
    assert "Q" in out and "C" in out
    assert "{question}" not in out


def test_render_missing_variable_raises_keyerror():
    with pytest.raises(KeyError, match="缺少变量"):
        load_prompt("structured_answer.v1").render(question="只有 question，没有 context")


def test_render_keeps_json_braces_intact():
    """正文含 JSON 示例时不能被当占位符（这就是不用 str.format 的原因）。"""
    p = Prompt(id="demo", version="1", model="", body='只输出 json，如 {"a": 1}。值：{x}')
    assert p.render(x="ok") == '只输出 json，如 {"a": 1}。值：ok'


def test_missing_front_matter_raises(tmp_path, monkeypatch):
    (tmp_path / "nofm.v1.md").write_text("没有 front matter", encoding="utf-8")
    monkeypatch.setattr(prompts, "get_settings", lambda: _SettingsStub(tmp_path))
    load_prompt.cache_clear()
    try:
        with pytest.raises(ValueError, match="缺少 front matter"):
            load_prompt("nofm.v1")
    finally:
        load_prompt.cache_clear()


def test_missing_file_raises_filenotfound(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts, "get_settings", lambda: _SettingsStub(tmp_path))
    load_prompt.cache_clear()
    try:
        with pytest.raises(FileNotFoundError):
            load_prompt("not_exists.v9")
    finally:
        load_prompt.cache_clear()
