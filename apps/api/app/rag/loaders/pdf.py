from pathlib import Path

from pypdf import PdfReader

from app.rag.models import Document


def load_pdf(path: Path, root: Path, workspace: str) -> Document | None:
    reader = PdfReader(str(path))
    text = "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if len(text) < 50:
        print(f"疑似扫描件，跳过: {path}")
        return None
    title = (reader.metadata and reader.metadata.title) or path.stem
    return Document.create(
        text=text,
        source=path.relative_to(root).as_posix(),
        title=title,
        type="pdf",
        workspace=workspace,
        mtime=path.stat().st_mtime,
    )
