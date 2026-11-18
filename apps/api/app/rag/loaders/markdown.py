import re
from pathlib import Path

import yaml

from app.rag.models import Document

_FM = re.compile(r"^---\n(.*?)\n---\n", re.S)


def load_markdown(path: Path, root: Path, workspace: str) -> Document:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    title = None
    if m := _FM.match(raw):  # React/Vite 文档常带 front matter
        meta = yaml.safe_load(m.group(1)) or {}
        title = meta.get("title") if isinstance(meta, dict) else None
        raw = raw[m.end() :]
    text = raw.strip()
    if not title:
        title = next(
            (ln.lstrip("#").strip() for ln in text.splitlines() if ln.startswith("# ")),
            path.stem,
        )
    return Document.create(
        text=text,
        source=path.relative_to(root).as_posix(),
        title=title,
        type="md",
        workspace=workspace,
        mtime=path.stat().st_mtime,
    )
