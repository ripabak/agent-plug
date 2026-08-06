"""Unit tests for the RAG retrieval tool (used by the agent)."""
import hashlib

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

from app.agent.tools import create_rag_tool, format_docs
from app.rag.splitter import split_text


class FakeEmbeddings(Embeddings):
    def _vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [(b / 255.0) for b in digest[:8]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


def _build_store() -> InMemoryVectorStore:
    store = InMemoryVectorStore(FakeEmbeddings())
    from langchain_core.documents import Document

    docs = [
        Document(
            page_content=chunk,
            metadata={"url": "https://example.com/pricing", "title": "Pricing", "source_id": 1, "agent_id": 1},
        )
        for chunk in split_text("Our pricing starts at $19 per month. " * 10, chunk_size=40, chunk_overlap=5)
    ]
    store.add_documents(docs)
    return store


@pytest.mark.asyncio
async def test_tool_returns_citations():
    tool = create_rag_tool(agent_id=1, store=_build_store())
    result = await tool.ainvoke({"query": "pricing per month"})
    assert "[Source: https://example.com/pricing" in result
    assert "pricing" in result.lower() or "$19" in result


@pytest.mark.asyncio
async def test_tool_empty_store_informs_agent():
    tool = create_rag_tool(agent_id=1, store=InMemoryVectorStore(FakeEmbeddings()))
    result = await tool.ainvoke({"query": "anything"})
    assert "No relevant content found" in result


def test_format_docs_uses_url_and_title():
    from langchain_core.documents import Document

    docs = [
        Document(
            page_content="chunk text",
            metadata={"url": "https://x.com/page", "title": "Page Title", "source_id": 1, "agent_id": 1},
        )
    ]
    out = format_docs(docs)
    assert "[Source: https://x.com/page | Page Title]" in out
    assert "chunk text" in out
