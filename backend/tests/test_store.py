"""Unit tests for the RAG store manager (InMemoryVectorStore per agent)."""
import hashlib

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.rag.splitter import split_text
from app.rag.store import RAGStoreManager


class FakeEmbeddings(Embeddings):
    """Deterministic hash-based embeddings (no network)."""

    def _vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [(b / 255.0) for b in digest[:8]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


def _docs(agent_id: int, source_id: int, text: str) -> list[Document]:
    return [
        Document(
            page_content=chunk,
            metadata={"url": "https://example.com/a", "title": "A", "source_id": source_id, "agent_id": agent_id},
        )
        for chunk in split_text(text, chunk_size=50, chunk_overlap=10)
    ]


@pytest.mark.asyncio
async def test_add_and_search_returns_sources():
    mgr = RAGStoreManager(FakeEmbeddings())
    docs = _docs(agent_id=1, source_id=10, text="Apple banana cherry. " * 20)
    ids = mgr.add_documents(1, 10, docs)
    assert len(ids) == len(docs)

    results = await mgr.asearch(1, "apple banana", k=2)
    assert len(results) == 2
    assert all(doc.metadata["url"] == "https://example.com/a" for doc in results)
    assert all(doc.metadata["source_id"] == 10 for doc in results)


@pytest.mark.asyncio
async def test_stores_are_isolated_per_agent():
    mgr = RAGStoreManager(FakeEmbeddings())
    mgr.add_documents(1, 1, _docs(1, 1, "apple " * 50))
    mgr.add_documents(2, 2, _docs(2, 2, "banana " * 50))
    # Agent 1's store must never surface agent 2's docs (and vice versa).
    assert all(doc.metadata["source_id"] == 1 for doc in await mgr.asearch(1, "banana", k=3))
    assert all(doc.metadata["source_id"] == 2 for doc in await mgr.asearch(2, "apple", k=3))


@pytest.mark.asyncio
async def test_delete_source_removes_only_that_source():
    mgr = RAGStoreManager(FakeEmbeddings())
    mgr.add_documents(1, 10, _docs(1, 10, "apple " * 40))
    mgr.add_documents(1, 11, _docs(1, 11, "cherry " * 40))

    removed = mgr.delete_source(1, 10)
    assert removed > 0

    apple_hits = await mgr.asearch(1, "apple", k=10)
    assert all(doc.metadata["source_id"] != 10 for doc in apple_hits)
    cherry_hits = await mgr.asearch(1, "cherry", k=10)
    assert len(cherry_hits) > 0


@pytest.mark.asyncio
async def test_delete_agent_drops_store():
    mgr = RAGStoreManager(FakeEmbeddings())
    mgr.add_documents(1, 1, _docs(1, 1, "apple " * 40))
    mgr.delete_agent(1)
    assert await mgr.asearch(1, "apple", k=5) == []

