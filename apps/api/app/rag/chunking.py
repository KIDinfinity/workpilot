import re
import uuid

from pydantic import BaseModel

from app.rag.models import Document

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


class Chunk(BaseModel):
    id: str
    doc_id: str
    text: str
    section: str
    order: int
    metadata: dict


def split_sections(text: str) -> list[tuple[str, str]]:
    stack: list[tuple[int, str]] = []
    out, buf, in_code = [], [], False

    def flush():
        body = "\n".join(buf).strip()
        if body:
            out.append((" > ".join(t for _, t in stack), body))
        buf.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        m = None if in_code else _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2)))
        else:
            buf.append(line)
    flush()
    return out


def split_body(body: str, size: int, overlap: int) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    step = max(size - overlap, 1)
    pieces: list[str] = []
    for p in paras:  # 超长段落先按 size 硬切（带 overlap）
        pieces += [p[i : i + size] for i in range(0, len(p), step)] if len(p) > size else [p]
    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + len(p) + 2 > size:
            chunks.append(cur)
            cur = (cur[-overlap:] + "\n\n" + p) if overlap else p  # 带上前一块尾部作为 overlap
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def chunk_document(doc: Document, size: int = 600, overlap: int = 100) -> list[Chunk]:
    out: list[Chunk] = []
    for section, body in split_sections(doc.text):
        for piece in split_body(body, size, overlap):
            order = len(out)
            out.append(
                Chunk(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.id}:{order}")),
                    doc_id=doc.id,
                    text=piece,
                    section=section or doc.title,
                    order=order,
                    metadata={
                        "source": doc.source,
                        "title": doc.title,
                        "workspace": doc.metadata.workspace,
                    },
                )
            )
    return out
