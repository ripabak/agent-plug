"""Knowledge base routes: add/list/delete/reindex URL sources and PDF uploads."""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..config import UPLOAD_DIR, UPLOAD_MAX_FILES, UPLOAD_MAX_SIZE
from ..database import get_db
from ..models import Agent, Source, User
from ..rag import store_manager
from ..rag.fetcher import validate_url
from ..rag.pipeline import index_pending_sources, reindex_agent
from ..schemas import ReindexRequest, SourceCreate, SourceResponse, TextSourceCreate

router = APIRouter(prefix="/api/agents/{agent_id}/sources", tags=["knowledge"])


async def _get_owned_agent(db: AsyncSession, agent_id: int, user: User) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("", response_model=list[SourceResponse], status_code=status.HTTP_201_CREATED)
async def add_sources(
    agent_id: int,
    data: SourceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add URL sources (deduped) and kick off background indexing."""
    await _get_owned_agent(db, agent_id, user)

    existing = (
        await db.execute(select(Source.url).where(Source.agent_id == agent_id))
    ).scalars().all()
    existing_set = set(existing)

    created: list[Source] = []
    for raw_url in data.urls:
        try:
            url = validate_url(raw_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
        if url in existing_set:
            continue
        source = Source(agent_id=agent_id, url=url, status="pending")
        db.add(source)
        created.append(source)
        existing_set.add(url)

    if created:
        await db.commit()
        for s in created:
            await db.refresh(s)
        # Fire-and-forget indexing; frontend polls status.
        await index_pending_sources(agent_id)

    return [SourceResponse.model_validate(s) for s in created]


@router.post("/files", response_model=list[SourceResponse], status_code=status.HTTP_201_CREATED)
async def upload_source_files(
    agent_id: int,
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload PDF files as knowledge sources (multipart, 1..%d files)."""
    await _get_owned_agent(db, agent_id, user)

    if not files:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No files provided")
    if len(files) > UPLOAD_MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"At most {UPLOAD_MAX_FILES} files per request",
        )

    created: list[Source] = []
    agent_dir = Path(UPLOAD_DIR) / str(agent_id)
    agent_dir.mkdir(parents=True, exist_ok=True)

    for upload in files:
        name = upload.filename or ""
        if not name.lower().endswith(".pdf"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{name!r} is not a PDF")
        data = await upload.read()
        if len(data) > UPLOAD_MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{name!r} exceeds the {UPLOAD_MAX_SIZE // (1024 * 1024)}MB limit",
            )

        rel_path = f"{agent_id}/{uuid.uuid4().hex}.pdf"
        (agent_dir / Path(rel_path).name).write_bytes(data)

        source = Source(
            agent_id=agent_id,
            url=f"file://{rel_path}",
            kind="pdf",
            file_name=name,
            file_path=rel_path,
            file_size=len(data),
            status="pending",
        )
        db.add(source)
        created.append(source)

    await db.commit()
    for s in created:
        await db.refresh(s)
    await index_pending_sources(agent_id)

    return [SourceResponse.model_validate(s) for s in created]


@router.post("/text", response_model=list[SourceResponse], status_code=status.HTTP_201_CREATED)
async def add_text_source(
    agent_id: int,
    data: TextSourceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add pasted long-form text as a knowledge source (kind=text)."""
    await _get_owned_agent(db, agent_id, user)

    content = data.content.strip()
    if len(content) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text content is too short (min 10 characters)",
        )

    source = Source(
        agent_id=agent_id,
        url=f"text://{uuid.uuid4().hex}",
        kind="text",
        title=data.title.strip() or "Pasted text",
        text_content=content,
        status="pending",
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    await index_pending_sources(agent_id)
    return [SourceResponse.model_validate(source)]


@router.get("", response_model=list[SourceResponse])
async def list_sources(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List sources with their indexing status."""
    await _get_owned_agent(db, agent_id, user)
    result = await db.execute(
        select(Source).where(Source.agent_id == agent_id).order_by(Source.created_at.desc())
    )
    return [SourceResponse.model_validate(s) for s in result.scalars().all()]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    agent_id: int,
    source_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a source and remove its chunks from the in-memory index."""
    await _get_owned_agent(db, agent_id, user)
    result = await db.execute(
        select(Source).where(Source.id == source_id, Source.agent_id == agent_id)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    store_manager.delete_source(agent_id, source_id)
    # Remove the stored PDF file (if any) from disk.
    if source.file_path:
        try:
            os.remove(os.path.join(UPLOAD_DIR, source.file_path))
        except OSError:
            pass  # best-effort file cleanup
    await db.delete(source)
    await db.commit()


@router.post("/reindex", response_model=dict)
async def reindex_sources(
    agent_id: int,
    data: ReindexRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-index all (or only failed) sources; returns how many were scheduled."""
    await _get_owned_agent(db, agent_id, user)
    only_failed = (data.only_failed if data else False)
    count = await reindex_agent(agent_id, only_failed=only_failed)
    return {"scheduled": count}
