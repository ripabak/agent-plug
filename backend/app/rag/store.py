"""pgvector-backed vector store management, one PGVector collection per agent.

Chunks live in PostgreSQL (`langchain_pg_collection` / `langchain_pg_embedding`
tables) via langchain-postgres `PGVector`; each agent gets its own collection
(`agent_{agent_id}`) so retrieval and deletion are scoped per agent. Chunk ids
are tracked per source — in memory for the current process and persisted on the
`source.chunk_ids` column so deletions stay correct across restarts. Each chunk
carries metadata {url, title, source_id, agent_id} so the agent can cite where
information came from and sources can be deleted.
"""
import asyncio
import os
import uuid

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy.pool import NullPool

from ..config import VECTOR_DB_URL


def _engine_args() -> dict:
    # NullPool under tests: each op gets a fresh connection bound to the
    # current event loop (mirrors app/database.py).
    if os.getenv("AP_TESTING") == "1":
        return {"poolclass": NullPool}
    return {}


class RAGStoreManager:
    """Owns one PGVector collection per agent id + chunk-id bookkeeping."""

    def __init__(self, embeddings: Embeddings, connection: str = VECTOR_DB_URL) -> None:
        self._embeddings = embeddings
        self._connection = connection
        self._stores: dict[int, PGVector] = {}
        self._init_locks: dict[int, asyncio.Lock] = {}
        # agent_id -> source_id -> list[chunk ids] (process-local bookkeeping)
        self._source_chunks: dict[int, dict[int, list[str]]] = {}

    def _collection_name(self, agent_id: int) -> str:
        return f"agent_{agent_id}"

    async def _ensure_store(self, agent_id: int) -> PGVector:
        """Get (or lazily create + initialize) the agent's collection store."""
        store = self._stores.get(agent_id)
        if store is not None:
            return store
        lock = self._init_locks.setdefault(agent_id, asyncio.Lock())
        async with lock:
            store = self._stores.get(agent_id)
            if store is not None:
                return store
            store = PGVector(
                embeddings=self._embeddings,
                connection=self._connection,
                collection_name=self._collection_name(agent_id),
                async_mode=True,
                engine_args=_engine_args(),
            )
            # Eager async init (extension + tables + collection) under our lock
            # so PGVector's lazy `__apost_init__` never races between coroutines.
            await store.acreate_collection()
            self._stores[agent_id] = store
            self._source_chunks.setdefault(agent_id, {})
            return store

    # --- mutation ---
    async def add_documents(self, agent_id: int, source_id: int, docs: list[Document]) -> list[str]:
        """Add docs to the agent's collection, tracking ids per source."""
        store = await self._ensure_store(agent_id)
        ids: list[str] = []
        for doc in docs:
            doc_id = doc.id or uuid.uuid4().hex
            doc.id = doc_id
            ids.append(doc_id)
        await store.aadd_documents(docs, ids=ids)
        self._source_chunks[agent_id].setdefault(source_id, []).extend(ids)
        return ids

    async def delete_source(self, agent_id: int, source_id: int, ids: list[str] | None = None) -> int:
        """Delete all chunks belonging to a source; returns removed count.

        `ids` are the persisted chunk ids (`source.chunk_ids`); they are merged
        with any in-process bookkeeping so deletes are correct even after a
        restart, when the process-local bookkeeping is gone.
        """
        store = self._stores.get(agent_id)
        tracked = self._source_chunks.get(agent_id, {}).pop(source_id, [])
        ids = list(dict.fromkeys([*(ids or []), *tracked]))
        if store and ids:
            await store.adelete(ids=ids, collection_only=True)
        return len(ids)

    async def delete_agent(self, agent_id: int) -> None:
        """Drop the agent's collection entirely (on agent deletion)."""
        store = self._stores.pop(agent_id, None)
        self._source_chunks.pop(agent_id, None)
        self._init_locks.pop(agent_id, None)
        if store is None:
            # Collection may still exist in PG after a restart; build a store
            # handle just to drop it (adelete_collection is a no-op if missing).
            store = PGVector(
                embeddings=self._embeddings,
                connection=self._connection,
                collection_name=self._collection_name(agent_id),
                async_mode=True,
                engine_args=_engine_args(),
            )
        await store.adelete_collection()

    # --- search helper (used by the agent tool) ---
    async def asearch(self, agent_id: int, query: str, k: int) -> list[Document]:
        """Async similarity search on the agent's collection (empty list if none)."""
        store = self._stores.get(agent_id)
        if store is None:
            return []
        return await store.asimilarity_search(query, k=k)
