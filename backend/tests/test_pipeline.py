"""Integration tests for the RAG indexing pipeline (uses test DB + fake fetch)."""
import hashlib
import uuid

import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import select

from app.database import async_session
from app.models import Agent, Source, User
from app.rag.fetcher import Page
from app.rag.pipeline import index_source, rebuild_all
from app.rag.store import RAGStoreManager


class FakeEmbeddings(Embeddings):
    def _vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [(b / 255.0) for b in digest[:8]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


async def _seed_agent_and_source(url: str = "https://example.com/docs") -> tuple[int, int]:
    async with async_session() as db:
        user = User(email=f"pipe-{uuid.uuid4().hex}@example.com", display_name="Pipe", hashed_password="x")
        db.add(user)
        await db.flush()
        agent = Agent(user_id=user.id, name="Pipeline Bot", public_token=f"tok_{uuid.uuid4().hex}")
        db.add(agent)
        await db.flush()
        source = Source(agent_id=agent.id, url=url, status="pending")
        db.add(source)
        await db.commit()
        return agent.id, source.id


async def _load_source(source_id: int) -> Source:
    async with async_session() as db:
        return (await db.execute(select(Source).where(Source.id == source_id))).scalar_one()


@pytest.mark.asyncio
async def test_index_source_success(monkeypatch):
    mgr = RAGStoreManager(FakeEmbeddings())
    agent_id, source_id = await _seed_agent_and_source()

    monkeypatch.setattr(
        "app.rag.pipeline.fetch_page",
        lambda url, client=None: Page(url=url, title="Example Docs", text="RAG content about widgets. " * 30),
    )

    await index_source(source_id, mgr)

    src = await _load_source(source_id)
    assert src.status == "ready"
    assert src.title == "Example Docs"
    assert src.chunk_count > 0

    results = await mgr.asearch(agent_id, "widgets", k=3)
    assert len(results) > 0
    assert results[0].metadata["url"] == "https://example.com/docs"
    assert results[0].metadata["source_id"] == source_id


@pytest.mark.asyncio
async def test_index_source_failure_is_isolated(monkeypatch):
    mgr = RAGStoreManager(FakeEmbeddings())
    agent_id, source_id = await _seed_agent_and_source()

    def boom(url, client=None):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.rag.pipeline.fetch_page", boom)

    await index_source(source_id, mgr)

    src = await _load_source(source_id)
    assert src.status == "failed"
    assert "network down" in (src.error or "")
    # store untouched (no chunks added)
    assert await mgr.asearch(agent_id, "anything", k=3) == []


@pytest.mark.asyncio
async def test_indexing_concurrency_is_bounded(monkeypatch):
    """With INDEX_CONCURRENCY=2, at most 2 sources index at once; the rest queue."""
    import threading
    import time

    from app.rag.pipeline import index_pending_sources

    monkeypatch.setattr("app.rag.pipeline.INDEX_CONCURRENCY", 2)

    mgr = RAGStoreManager(FakeEmbeddings())
    async with async_session() as db:
        user = User(email=f"pipe-{uuid.uuid4().hex}@example.com", display_name="Pipe", hashed_password="x")
        db.add(user)
        await db.flush()
        agent = Agent(user_id=user.id, name="Pipeline Bot", public_token=f"tok_{uuid.uuid4().hex}")
        db.add(agent)
        await db.flush()
        for i in range(4):
            db.add(Source(agent_id=agent.id, url=f"https://example.com/{i}", status="pending"))
        await db.commit()
        agent_id = agent.id

    # Track peak concurrent fetches (fetch_page runs in a thread via to_thread).
    stats = {"active": 0, "max": 0}
    guard = threading.Lock()

    def slow_fetch(url, client=None):
        with guard:
            stats["active"] += 1
            stats["max"] = max(stats["max"], stats["active"])
        time.sleep(0.05)
        with guard:
            stats["active"] -= 1
        return Page(url=url, title="T", text="queue content " * 20)

    monkeypatch.setattr("app.rag.pipeline.fetch_page", slow_fetch)

    processed = await index_pending_sources(agent_id, mgr)

    assert processed == 4
    assert stats["max"] == 2, "more than INDEX_CONCURRENCY sources ran at once"
    async with async_session() as db:
        statuses = (
            (await db.execute(select(Source.status).where(Source.agent_id == agent_id)))
            .scalars()
            .all()
        )
    assert set(statuses) == {"ready"}


@pytest.mark.asyncio
async def test_rebuild_all(monkeypatch):
    mgr = RAGStoreManager(FakeEmbeddings())
    agent_id, source_id = await _seed_agent_and_source()
    monkeypatch.setattr(
        "app.rag.pipeline.fetch_page",
        lambda url, client=None: Page(url=url, title="T", text="content " * 40),
    )

    total = await rebuild_all(mgr)
    assert total >= 1
    assert len(await mgr.asearch(agent_id, "content", k=5)) > 0
