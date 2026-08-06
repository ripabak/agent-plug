"""RAG indexing pipeline: fetch → parse → chunk → embed → store → status.

Each source row in Postgres drives the pipeline; the per-agent
InMemoryVectorStore holds the chunks with {url, title, source_id, agent_id}
metadata so answers can cite sources and sources can be deleted.
"""
import asyncio
import os

from langchain_core.documents import Document
from sqlalchemy import select, update

from ..config import UPLOAD_DIR
from ..database import async_session
from ..models import Source
from . import store_manager
from .fetcher import fetch_page
from .pdf import parse_pdf
from .splitter import split_text


async def _load_source_text(source: Source) -> tuple[str, str]:
    """Return (text, title) for a source, depending on its kind."""
    if source.kind == "text":
        # Pasted long text: stored directly in the DB.
        return source.text_content or "", source.title or "Pasted text"
    if source.kind == "pdf":
        # Uploaded PDF: read the stored file from disk (no network).
        path = os.path.join(UPLOAD_DIR, source.file_path or "")
        text = await asyncio.to_thread(parse_pdf, path)
        title = (source.file_name or "document").rsplit(".", 1)[0]
        return text, title
    # URL source: fetch + parse the HTML page.
    page = await asyncio.to_thread(fetch_page, source.url)
    return page.text, page.title


async def index_source(source_id: int, mgr=store_manager) -> None:
    """Index one source end-to-end, updating its status row as it goes."""
    async with async_session() as db:
        source = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
        if source is None:
            return
        agent_id = source.agent_id
        source.status = "fetching"
        source.error = None
        await db.commit()

    try:
        # Load content off the event loop (URL fetch or PDF parse).
        text, title = await _load_source_text(source)

        async with async_session() as db:
            src = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one()
            src.status = "indexing"
            src.title = title
            await db.commit()

        chunks = split_text(text)
        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "url": source.url,
                    "title": title,
                    "source_id": source_id,
                    "agent_id": agent_id,
                },
            )
            for chunk in chunks
        ]

        # Re-index clears previous chunks of this source first (idempotent).
        mgr.delete_source(agent_id, source_id)
        mgr.add_documents(agent_id, source_id, docs)

        async with async_session() as db:
            src = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one()
            src.status = "ready"
            src.chunk_count = len(chunks)
            src.error = None
            await db.commit()
    except Exception as exc:  # per-URL failure isolation
        async with async_session() as db:
            src = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one()
            src.status = "failed"
            src.chunk_count = 0
            src.error = str(exc)[:500]
            await db.commit()


def _lock_for(agent_id: int) -> asyncio.Lock:
    lock = _agent_locks.get(agent_id)
    if lock is None:
        lock = asyncio.Lock()
        _agent_locks[agent_id] = lock
    return lock


_agent_locks: dict[int, asyncio.Lock] = {}


async def _run_sources(agent_id: int, statuses: tuple[str, ...], mgr=store_manager) -> int:
    """Process an agent's sources matching `statuses`, draining new ones.

    Returns the number of sources processed, or 0 if the agent is already
    being indexed by another task.
    """
    lock = _lock_for(agent_id)
    if lock.locked():
        return 0
    async with lock:
        processed = 0
        for _ in range(50):  # drain loop: catches sources added mid-run
            async with async_session() as db:
                rows = (
                    await db.execute(
                        select(Source).where(
                            Source.agent_id == agent_id,
                            Source.status.in_(statuses),
                        )
                    )
                ).scalars().all()
            if not rows:
                break
            await asyncio.gather(
                *(asyncio.create_task(index_source(r.id, mgr)) for r in rows),
                return_exceptions=True,
            )
            processed += len(rows)
        return processed


async def index_pending_sources(agent_id: int, mgr=store_manager) -> int:
    """Index sources that are pending or failed (used after adding URLs)."""
    return await _run_sources(agent_id, ("pending", "failed"), mgr)


async def reindex_agent(agent_id: int, only_failed: bool = False, mgr=store_manager) -> int:
    """Re-index all (or only failed) sources of an agent."""
    if only_failed:
        return await _run_sources(agent_id, ("failed",), mgr)
    async with async_session() as db:
        await db.execute(
            update(Source).where(Source.agent_id == agent_id).values(status="pending")
        )
        await db.commit()
    return await _run_sources(agent_id, ("pending",), mgr)


async def rebuild_all(mgr=store_manager) -> int:
    """Rebuild every agent's in-memory index from stored sources (startup)."""
    async with async_session() as db:
        agent_ids = (await db.execute(select(Source.agent_id).distinct())).scalars().all()
    total = 0
    for agent_id in agent_ids:
        total += await reindex_agent(agent_id, mgr=mgr)
    return total
