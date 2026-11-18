from pathlib import Path

from app.rag.loaders.html import load_html
from app.rag.loaders.markdown import load_markdown
from app.rag.loaders.pdf import load_pdf
from app.rag.models import Document

LOADERS = {
    ".md": load_markdown,
    ".pdf": load_pdf,
    ".html": load_html,
    ".htm": load_html,
    ".txt": load_markdown,  # 纯文本按 Markdown 子集处理（无 front matter / 标题时用文件名）
}


def load_dir(root: Path, workspace: str = "default") -> tuple[list[Document], int]:
    docs: list[Document] = []
    seen: set[str] = set()
    dup = 0
    for p in sorted(root.rglob("*")):
        fn = LOADERS.get(p.suffix.lower())
        if not fn or p.name == "SOURCES.md":
            continue
        doc = fn(p, root, workspace)
        if doc is None or not doc.text.strip():
            continue
        if doc.id in seen:
            dup += 1
            continue
        seen.add(doc.id)
        docs.append(doc)
    return docs, dup


def load_file(
    path: Path,
    *,
    doc_id: str,
    title: str,
    workspace: str = "default",
) -> Document | None:
    """加载单个上传文件，并把 doc.id 覆盖为上传记录 id。

    CLI 批量导入时 doc.id 是 sha256(text)；上传场景下删除/查分块要按
    `doc_id` 过滤 Qdrant，因此让 doc.id = KBDocument.id，title = 用户文件名。
    """
    fn = LOADERS.get(path.suffix.lower())
    if fn is None:
        return None
    doc = fn(path, path.parent, workspace)  # root=父目录，source 即文件名
    if doc is None or not doc.text.strip():
        return None
    return Document(
        id=doc_id,
        source=path.name,
        title=title,
        text=doc.text,
        metadata=doc.metadata,
    )
