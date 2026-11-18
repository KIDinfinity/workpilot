from app.rag.chunking import chunk_document, split_body, split_sections
from app.rag.models import Document


def make_doc(text: str, source: str = "t.md") -> Document:
    return Document.create(
        text=text, source=source, title="T", type="md", workspace="default", mtime=0
    )


def test_heading_path_joined():
    sections = split_sections("# A\n## B\n内容")
    assert sections == [("A > B", "内容")]


def test_codeblock_hash_not_heading():
    text = "# A\n```python\n# 这不是标题\nx = 1\n```\n内容"
    sections = split_sections(text)
    assert len(sections) == 1
    assert sections[0][0] == "A"
    assert "# 这不是标题" in sections[0][1]


def test_long_paragraph_hard_split_bounded():
    body = "".join(f"{i:04d}" for i in range(500))  # 2000 字无空行
    chunks = split_body(body, size=600, overlap=100)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c) <= 602 + 100  # size + overlap + 分隔符 2 字符


def test_adjacent_chunks_overlap():
    body = "".join(f"{i:04d}" for i in range(500))
    chunks = split_body(body, size=600, overlap=100)
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        assert nxt[:50] in prev


def test_chunk_id_deterministic():
    text = "# A\n\n段落一。\n\n" + "长段落" * 200
    doc = make_doc(text)
    ids_a = [c.id for c in chunk_document(doc)]
    ids_b = [c.id for c in chunk_document(doc)]
    assert ids_a == ids_b
    assert len(ids_a) > 0


def test_chunk_payload_fields():
    doc = make_doc("# 标题\n\n正文内容")
    chunks = chunk_document(doc)
    c = chunks[0]
    assert c.doc_id == doc.id
    assert c.section == "标题"
    assert c.order == 0
    assert c.metadata["source"] == "t.md"
    assert c.metadata["workspace"] == "default"
