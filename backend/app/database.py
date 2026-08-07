"""Async SQLAlchemy engine/session + table creation (MVP: create_all, no alembic)."""
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import DATABASE_URL

# NullPool under tests: each session gets a fresh connection bound to the
# current event loop (avoids cross-loop affinity issues between fixtures
# and the app's portal loop).
_poolclass = NullPool if os.getenv("AP_TESTING") == "1" else None
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, poolclass=_poolclass)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency: yields a session (one per request)."""
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create all tables if they don't exist (used in app lifespan and tests)."""
    async with engine.begin() as conn:
        # pgvector extension must exist before langchain-postgres creates the
        # vector tables (idempotent; the postgres role can install it).
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent migrations for existing dev databases (MVP: no alembic).
        for statement in (
            "ALTER TABLE source ADD COLUMN IF NOT EXISTS chunk_ids JSONB",
            "ALTER TABLE source ADD COLUMN IF NOT EXISTS kind VARCHAR NOT NULL DEFAULT 'url'",
            "ALTER TABLE source ADD COLUMN IF NOT EXISTS file_name VARCHAR",
            "ALTER TABLE source ADD COLUMN IF NOT EXISTS file_path VARCHAR",
            "ALTER TABLE source ADD COLUMN IF NOT EXISTS file_size INTEGER",
            "ALTER TABLE source ADD COLUMN IF NOT EXISTS text_content TEXT",
            "ALTER TABLE agent_usage ADD COLUMN IF NOT EXISTS country VARCHAR",
            "ALTER TABLE agent_usage ADD COLUMN IF NOT EXISTS page_url VARCHAR",
            "ALTER TABLE agent ADD COLUMN IF NOT EXISTS avatar_path VARCHAR",
            "ALTER TABLE agent ADD COLUMN IF NOT EXISTS avatar_kind VARCHAR NOT NULL DEFAULT 'photo'",
            "ALTER TABLE agent ADD COLUMN IF NOT EXISTS chat_theme TEXT DEFAULT ''",
            "ALTER TABLE agent ADD COLUMN IF NOT EXISTS persona_prompt TEXT",
            "ALTER TABLE agent ADD COLUMN IF NOT EXISTS show_thinking BOOLEAN DEFAULT TRUE",
            "ALTER TABLE agent ADD COLUMN IF NOT EXISTS show_tools BOOLEAN DEFAULT TRUE",
            "ALTER TABLE agent_thread ADD COLUMN IF NOT EXISTS page_url VARCHAR",
            # Dead columns removed (the theme lives in chat_theme now; the
            # system prompt is composed server-side, never stored per-agent;
            # all chats run through the public widget protocol now, so the
            # authed-thread user link and the preview/widget channel split
            # are gone).
            "ALTER TABLE agent DROP COLUMN IF EXISTS theme_color",
            "ALTER TABLE agent DROP COLUMN IF EXISTS system_prompt",
            "ALTER TABLE agent_thread DROP COLUMN IF EXISTS user_id",
            "ALTER TABLE agent_usage DROP COLUMN IF EXISTS channel",
        ):
            await conn.execute(text(statement))
