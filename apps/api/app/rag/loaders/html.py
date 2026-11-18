from pathlib import Path

import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

from app.rag.models import Document


def _extract_markdown(raw: bytes) -> str | None:
    text = trafilatura.extract(
        raw, output_format="markdown", include_tables=True, include_links=False
    )
    if text and text.strip():
        return text.strip()
    # 回退：正文太短或结构特殊，用 bs4 取 main/article/body + markdownify
    soup = BeautifulSoup(raw, "html.parser")
    node = soup.find("main") or soup.find("article") or soup.body
    if node is None:
        return None
    return markdownify(str(node), heading_style="ATX").strip()


def _extract_title(raw: bytes) -> str | None:
    soup = BeautifulSoup(raw, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None


def load_html(path: Path, root: Path, workspace: str) -> Document | None:
    raw = path.read_bytes()
    text = _extract_markdown(raw)
    if not text or len(text) < 50:
        print(f"疑似空正文，跳过: {path}")
        return None
    title = _extract_title(raw) or path.stem
    return Document.create(
        text=text,
        source=path.relative_to(root).as_posix(),
        title=title,
        type="html",
        workspace=workspace,
        mtime=path.stat().st_mtime,
    )
