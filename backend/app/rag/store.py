"""In-memory vector store management, one InMemoryVectorStore per agent.

MVP choice (per requirements): chunks live in `InMemoryVectorStore` and the
index is rebuilt from Postgres sources on startup. Each chunk carries metadata:
    {url, title, source_id, agent_id}
so the agent can cite where information came from and sources can be deleted.
"""
import uuid

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore


class RAGStoreManager:
    """Owns one InMemoryVectorStore per agent id + chunk-id bookkeeping."""

    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings
        self._stores: dict[int, InMemoryVectorStore] = {}
        # agent_id -> source_id -> list[chunk ids] (for targeted deletion)
        self._source_chunks: dict[int, dict[int, list[str]]] = {}

    def _ensure_store(self, agent_id: int) -> InMemoryVectorStore:
        if agent_id not in self._stores:
            self._stores[agent_id] = InMemoryVectorStore(self._embeddings)
            self._source_chunks[agent_id] = {}
        return self._stores[agent_id]

    # --- mutation ---
    def add_documents(self, agent_id: int, source_id: int, docs: list[Document]) -> list[str]:
        """Add docs to the agent's store, tracking ids per source."""
        store = self._ensure_store(agent_id)
        ids: list[str] = []
        for doc in docs:
            doc_id = doc.id or uuid.uuid4().hex
            doc.id = doc_id
            ids.append(doc_id)
        store.add_documents(docs, ids=ids)
        self._source_chunks[agent_id].setdefault(source_id, []).extend(ids)
        return ids

    def delete_source(self, agent_id: int, source_id: int) -> int:
        """Delete all chunks belonging to a source; returns removed count."""
        store = self._stores.get(agent_id)
        ids = self._source_chunks.get(agent_id, {}).pop(source_id, [])
        if store and ids:
            store.delete(ids=ids)
        return len(ids)

    def delete_agent(self, agent_id: int) -> None:
        """Drop the agent's store entirely (on agent deletion)."""
        self._stores.pop(agent_id, None)
        self._source_chunks.pop(agent_id, None)

    # --- search helper (used by the agent tool) ---
    async def asearch(self, agent_id: int, query: str, k: int) -> list[Document]:
        """Async similarity search on the agent's store (empty list if none)."""
        store = self._stores.get(agent_id)
        if store is None:
            return []
        return await store.asimilarity_search(query, k=k)
