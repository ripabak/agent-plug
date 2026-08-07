"""SQLAlchemy ORM models for Agent-Plug."""
import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .config import BACKEND_PUBLIC_URL


class User(Base):
    """Platform user (dashboard account)."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    agents: Mapped[list["Agent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Agent(Base):
    """An AI agent owned by a user; embeddable on external websites.

    `public_token` is the secret embedded in the widget snippet and used to
    authenticate the public (widget) endpoints.
    """

    __tablename__ = "agent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    welcome_message: Mapped[str] = mapped_column(String, default="Hi! How can I help you?")
    theme_color: Mapped[str] = mapped_column(String, default="#a9502a")
    avatar_emoji: Mapped[str] = mapped_column(String, default="🤖")
    # Storage key of the compressed avatar image (avatars/{agent_id}.webp);
    # None = fall back to avatar_emoji.
    avatar_path: Mapped[str | None] = mapped_column(String, nullable=True)
    # How the avatar renders in the widget: 'template' (animated GIF/emoji —
    # drawn on the header-colored circle, like the emoji avatar) or 'photo'
    # (uploaded logo — floats without a background color).
    avatar_kind: Mapped[str] = mapped_column(String, default="photo", nullable=False)

    @property
    def avatar_url(self) -> str | None:
        """Public URL for the avatar image (None if no photo uploaded).

        The storage key is stable (avatars/{agent_id}.webp) and the endpoint
        is browser-cacheable, so the URL is versioned with `?v=` (updated_at,
        microsecond precision) — replacing the photo busts the cache instead
        of showing the previous avatar.
        """
        if not self.avatar_path:
            return None
        version = self.updated_at.strftime("%Y%m%d%H%M%S%f") if self.updated_at else "0"
        return (
            f"{BACKEND_PUBLIC_URL.rstrip('/')}/api/public/agents/{self.id}/avatar"
            f"?v={version}"
        )
    # Chat display config, set from the dashboard preview and consumed by the
    # live widget: chat_theme is a JSON string {preset, custom, touched}
    # matching the frontend ChatThemeState; show_thinking/show_tools are the
    # client-side display toggles (the widget no longer adjusts them itself).
    chat_theme: Mapped[str] = mapped_column(Text, default="")
    show_thinking: Mapped[bool] = mapped_column(Boolean, default=False)
    show_tools: Mapped[bool] = mapped_column(Boolean, default=True)
    public_token: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="agents")
    sources: Mapped[list["Source"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="Source.created_at.desc()",
    )


class Source(Base):
    """A knowledge-base source for an agent (RAG input): URL or uploaded PDF."""

    __tablename__ = "source"
    __table_args__ = (UniqueConstraint("agent_id", "url", name="uq_source_agent_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    # 'url' = website source; 'pdf' = uploaded PDF file; 'text' = pasted long text.
    kind: Mapped[str] = mapped_column(String, default="url", nullable=False)
    file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Stored long-form text for kind='text' sources.
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # Chunk ids in the agent's pgvector collection (langchain_pg_embedding),
    # persisted so source deletions stay correct across restarts.
    chunk_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["Agent"] = relationship(back_populates="sources")


class AgentThread(Base):
    """Maps a namespaced thread key -> agent (+ optional user for authed chats)."""

    __tablename__ = "agent_thread"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    agent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent.id", ondelete="CASCADE"), nullable=False
    )
    # Null for public (widget) threads; set for dashboard preview threads.
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AgentUsage(Base):
    """One chat request (run) per agent: token counts for the usage dashboard.

    A row is written at the end of every agent run (preview or widget) with
    the aggregated usage of that request. Used by the Usage tab: request
    graph (row count per day), input/output token graph, and the paginated
    history list.
    """

    __tablename__ = "agent_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Where the request came from: 'preview' (dashboard) or 'widget' (public).
    channel: Mapped[str] = mapped_column(String, default="preview", nullable=False)
    thread_id: Mapped[str] = mapped_column(String, default="", nullable=False)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    # ISO 3166-1 alpha-2 country code of the client (resolved from IP).
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    # Terminal run state: completed / failed / cancelled.
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
