"""Tests for PDF parsing + PDF indexing in the RAG pipeline."""
import hashlib
import uuid
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import select

from app.config import UPLOAD_DIR
from app.database import async_session
from app.models import Agent, Source, User
from app.rag.pdf import parse_pdf
from app.rag.pipeline import index_source
from app.rag.store import RAGStoreManager


def make_pdf(text: str) -> bytes:
    """Build a small valid PDF (with proper xref table) containing `text`."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >> stream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj %s endobj\n" % (i, body)
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_pos,
    )
    return bytes(out)


class FakeEmbeddings(Embeddings):
    def _vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [(b / 255.0) for b in digest[:8]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class TestParsePdf:
    def test_extracts_text_from_pdf(self, tmp_path):
        path = tmp_path / "sample.pdf"
        path.write_bytes(make_pdf("Welcome to Agent Plug PDF testing"))
        text = parse_pdf(path)
        assert "Welcome to Agent Plug PDF testing" in text

    def test_empty_pdf_raises(self, tmp_path):
        path = tmp_path / "blank.pdf"
        path.write_bytes(make_pdf(""))
        with pytest.raises(ValueError):
            parse_pdf(path)


@pytest.mark.asyncio
async def test_index_pdf_source_end_to_end():
    """A kind=pdf source is read from disk, chunked, embedded, stored."""
    mgr = RAGStoreManager(FakeEmbeddings())

    # seed user/agent/source with a stored PDF file
    async with async_session() as db:
        user = User(email=f"pdf-{uuid.uuid4().hex}@example.com", display_name="P", hashed_password="x")
        db.add(user)
        await db.flush()
        agent = Agent(user_id=user.id, name="PDF Bot", public_token=f"tok_{uuid.uuid4().hex}")
        db.add(agent)
        await db.flush()

        rel = f"{agent.id}/{uuid.uuid4().hex}.pdf"
        full = Path(UPLOAD_DIR) / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(make_pdf("Quarterly report revenue grew twenty percent. " * 20))

        source = Source(
            agent_id=agent.id,
            url=f"file://{rel}",
            kind="pdf",
            file_name="quarterly-report.pdf",
            file_path=rel,
            file_size=full.stat().st_size,
            status="pending",
        )
        db.add(source)
        await db.commit()
        source_id = source.id
        agent_id = agent.id

    await index_source(source_id, mgr)

    async with async_session() as db:
        src = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one()
        assert src.status == "ready"
        assert src.title == "quarterly-report"
        assert src.chunk_count > 0

    results = await mgr.asearch(agent_id, "revenue", k=3)
    assert len(results) > 0
    # source metadata must carry the file:// identifier (citable)
    assert results[0].metadata["url"] == f"file://{rel}"


@pytest.mark.asyncio
async def test_index_text_source_end_to_end():
    """A kind=text source is chunked from its stored content (no fetch/file)."""
    mgr = RAGStoreManager(FakeEmbeddings())

    async with async_session() as db:
        user = User(email=f"txt-{uuid.uuid4().hex}@example.com", display_name="T", hashed_password="x")
        db.add(user)
        await db.flush()
        agent = Agent(user_id=user.id, name="Text Bot", public_token=f"tok_{uuid.uuid4().hex}")
        db.add(agent)
        await db.flush()
        source = Source(
            agent_id=agent.id,
            url=f"text://{uuid.uuid4().hex}",
            kind="text",
            title="FAQ Internal",
            text_content="The refund policy is thirty days from purchase. Refunds take five business days. " * 15,
            status="pending",
        )
        db.add(source)
        await db.commit()
        source_id = source.id
        agent_id = agent.id

    await index_source(source_id, mgr)

    async with async_session() as db:
        src = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one()
        assert src.status == "ready"
        assert src.chunk_count > 0

    results = await mgr.asearch(agent_id, "refund policy", k=3)
    assert len(results) > 0
    assert results[0].metadata["url"].startswith("text://")
    assert results[0].metadata["title"] == "FAQ Internal"
