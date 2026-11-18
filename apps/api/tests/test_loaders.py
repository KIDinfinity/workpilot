from pathlib import Path

from app.rag.loaders import load_dir
from app.rag.loaders.html import load_html
from app.rag.loaders.markdown import load_markdown
from app.rag.loaders.pdf import load_pdf

FIXTURES = Path(__file__).parent / "fixtures"


def test_markdown_frontmatter_title():
    doc = load_markdown(FIXTURES / "md_frontmatter.md", FIXTURES, "default")
    assert doc.title == "前端代码评审规范"
    assert "---" not in doc.text
    assert doc.metadata.type == "md"


def test_dedup_identical_content(tmp_path: Path):
    text = "# 相同内容\n\n用于测试内容哈希去重。\n"
    (tmp_path / "a.md").write_text(text, encoding="utf-8")
    (tmp_path / "b.md").write_text(text, encoding="utf-8")
    docs, dup = load_dir(tmp_path)
    assert len(docs) == 1
    assert dup == 1


def test_pdf_text_non_empty():
    doc = load_pdf(FIXTURES / "sample.pdf", FIXTURES, "default")
    assert doc is not None
    assert len(doc.text) > 0


def test_html_strips_nav_script():
    doc = load_html(FIXTURES / "sample.html", FIXTURES, "default")
    assert doc is not None
    assert "<nav" not in doc.text
    assert "<script" not in doc.text
    assert "正文关键词" in doc.text
