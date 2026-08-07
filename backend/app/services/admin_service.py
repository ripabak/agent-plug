"""Read-only admin analytics: platform stats, user list, user detail, usage.

Every query here is GET-only and admin-gated (`get_current_admin`); there are
no mutation endpoints — the admin can only monitor.
"""
import datetime as dt
from typing import Any

from sqlalchemy import Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Agent, AgentUsage, Source, User
from ..schemas import (
    AdminAgentRow,
    AdminStats,
    AdminUserRow,
    SourceResponse,
    UsageLog,
    UsagePoint,
    UsageSummary,
)
from .usage_service import DEFAULT_DAYS, MAX_DAYS, MAX_PAGE_SIZE

# Per-user aggregates reused by the list + detail queries.
_agent_counts = (
    select(Agent.user_id, func.count(Agent.id).label("agent_count"))
    .group_by(Agent.user_id)
    .subquery()
)

_usage_totals = (
    select(
        Agent.user_id,
        func.count(AgentUsage.id).label("requests"),
        func.coalesce(func.sum(AgentUsage.total_tokens), 0).label("tokens"),
        func.max(AgentUsage.created_at).label("last_active"),
    )
    .join(Agent, AgentUsage.agent_id == Agent.id)
    .group_by(Agent.user_id)
    .subquery()
)


def _user_row(row: Any) -> AdminUserRow:
    """Map a (user + aggregates) query row to AdminUserRow."""
    return AdminUserRow(
        id=int(row[0]),
        email=str(row[1]),
        display_name=str(row[2]),
        created_at=row[3],
        agent_count=int(row[4] or 0),
        total_requests=int(row[5] or 0),
        total_tokens=int(row[6] or 0),
        last_active=row[7],
    )


async def _get_user_row(db: AsyncSession, user_id: int) -> AdminUserRow | None:
    """One user + aggregates by id (None if not found)."""
    row = (
        await db.execute(
            select(
                User.id,
                User.email,
                User.display_name,
                User.created_at,
                func.coalesce(_agent_counts.c.agent_count, 0),
                func.coalesce(_usage_totals.c.requests, 0),
                func.coalesce(_usage_totals.c.tokens, 0),
                _usage_totals.c.last_active,
            )
            .outerjoin(_agent_counts, _agent_counts.c.user_id == User.id)
            .outerjoin(_usage_totals, _usage_totals.c.user_id == User.id)
            .where(User.id == user_id)
        )
    ).first()
    return _user_row(row) if row is not None else None


async def get_admin_stats(db: AsyncSession, days: int = DEFAULT_DAYS) -> AdminStats:
    """Platform-wide totals (all time) + daily request/token series."""
    days = max(1, min(days, MAX_DAYS))
    since = dt.datetime.now().replace(microsecond=0) - dt.timedelta(days=days - 1)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar_one()
    totals = (
        await db.execute(
            select(
                func.count(AgentUsage.id),
                func.coalesce(func.sum(AgentUsage.input_tokens), 0),
                func.coalesce(func.sum(AgentUsage.output_tokens), 0),
                func.coalesce(func.sum(AgentUsage.total_tokens), 0),
            )
        )
    ).one()
    total_requests, total_input, total_output, total_tokens = totals

    rows = (
        await db.execute(
            select(
                func.date_trunc("day", AgentUsage.created_at).cast(Date).label("day"),
                func.count(AgentUsage.id),
                func.coalesce(func.sum(AgentUsage.input_tokens), 0),
                func.coalesce(func.sum(AgentUsage.output_tokens), 0),
            )
            .where(AgentUsage.created_at >= since)
            .group_by("day")
            .order_by("day")
        )
    ).all()
    by_day = {str(row.day): row for row in rows}

    series: list[UsagePoint] = []
    for offset in range(days):
        day = (since + dt.timedelta(days=offset)).date()
        key = day.isoformat()
        row = by_day.get(key)
        series.append(
            UsagePoint(
                date=key,
                requests=row[1] if row else 0,
                input_tokens=row[2] if row else 0,
                output_tokens=row[3] if row else 0,
            )
        )

    return AdminStats(
        total_users=int(total_users),
        total_agents=int(total_agents),
        total_requests=int(total_requests),
        total_input_tokens=int(total_input),
        total_output_tokens=int(total_output),
        total_tokens=int(total_tokens),
        series=series,
    )


async def list_users(
    db: AsyncSession, q: str = "", page: int = 1, page_size: int = 20
) -> dict[str, Any]:
    """Paginated user list, searchable by email or display name (ILIKE)."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    filters = []
    if q.strip():
        like = f"%{q.strip()}%"
        filters.append(User.email.ilike(like) | User.display_name.ilike(like))

    total = (await db.execute(select(func.count(User.id)).where(*filters))).scalar_one()

    rows = (
        await db.execute(
            select(
                User.id,
                User.email,
                User.display_name,
                User.created_at,
                func.coalesce(_agent_counts.c.agent_count, 0),
                func.coalesce(_usage_totals.c.requests, 0),
                func.coalesce(_usage_totals.c.tokens, 0),
                _usage_totals.c.last_active,
            )
            .outerjoin(_agent_counts, _agent_counts.c.user_id == User.id)
            .outerjoin(_usage_totals, _usage_totals.c.user_id == User.id)
            .where(*filters)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return {
        "items": [_user_row(r) for r in rows],
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "pages": max(1, (int(total) + page_size - 1) // page_size),
    }


async def get_user_detail(db: AsyncSession, user_id: int) -> dict[str, Any] | None:
    """One user + their agents (with source/usage stats). None if not found."""
    user_row = await _get_user_row(db, user_id)
    if user_row is None:
        return None

    agents = (
        (
            await db.execute(
                select(Agent)
                .where(Agent.user_id == user_id)
                .order_by(Agent.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    agent_ids = [a.id for a in agents]

    usage_rows = (
        await db.execute(
            select(
                AgentUsage.agent_id,
                func.count(AgentUsage.id),
                func.coalesce(func.sum(AgentUsage.total_tokens), 0),
                func.max(AgentUsage.created_at),
            )
            .where(AgentUsage.agent_id.in_(agent_ids))
            .group_by(AgentUsage.agent_id)
        )
    ).all() if agent_ids else []
    usage_by_agent = {r[0]: r for r in usage_rows}

    source_rows = (
        await db.execute(
            select(
                Source.agent_id,
                func.count(Source.id),
                func.count(Source.id).filter(Source.status == "ready"),
            )
            .where(Source.agent_id.in_(agent_ids))
            .group_by(Source.agent_id)
        )
    ).all() if agent_ids else []
    sources_by_agent = {r[0]: r for r in source_rows}

    agent_rows = [
        AdminAgentRow(
            id=a.id,
            name=a.name,
            description=a.description or "",
            avatar_emoji=a.avatar_emoji,
            avatar_url=a.avatar_url,
            chat_theme=a.chat_theme or "",
            created_at=a.created_at,
            source_count=int((sources_by_agent.get(a.id) or (0, 0, 0))[1]),
            ready_sources=int((sources_by_agent.get(a.id) or (0, 0, 0))[2]),
            total_requests=int((usage_by_agent.get(a.id) or (0, 0, 0, None))[1]),
            total_tokens=int((usage_by_agent.get(a.id) or (0, 0, 0, None))[2]),
            last_active=(usage_by_agent.get(a.id) or (0, 0, 0, None))[3],
        )
        for a in agents
    ]

    return {"user": user_row, "agents": agent_rows}


async def get_agent_detail(db: AsyncSession, agent_id: int) -> dict[str, Any] | None:
    """One agent (any user) + its owner row. None if not found."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        return None
    user_row = await _get_user_row(db, agent.user_id)
    return {"agent": agent, "user": user_row} if user_row else None


async def get_agent_or_none(db: AsyncSession, agent_id: int) -> Agent | None:
    """Raw agent lookup for admin endpoints (404 handled by the router)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def get_agent_sources(db: AsyncSession, agent_id: int) -> list[Any]:
    """Sources of one agent, newest first (read-only)."""
    rows = (
        (
            await db.execute(
                select(Source)
                .where(Source.agent_id == agent_id)
                .order_by(Source.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [SourceResponse.model_validate(s) for s in rows]


async def get_user_usage(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10
) -> dict[str, Any]:
    """Paginated usage history across ALL of a user's agents + summary totals."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    totals = (
        await db.execute(
            select(
                func.count(AgentUsage.id),
                func.coalesce(func.sum(AgentUsage.input_tokens), 0),
                func.coalesce(func.sum(AgentUsage.output_tokens), 0),
                func.coalesce(func.sum(AgentUsage.total_tokens), 0),
            )
            .join(Agent, AgentUsage.agent_id == Agent.id)
            .where(Agent.user_id == user_id)
        )
    ).one()
    total_requests, total_input, total_output, total_tokens = totals

    rows = (
        await db.execute(
            select(AgentUsage, Agent.name)
            .join(Agent, AgentUsage.agent_id == Agent.id)
            .where(Agent.user_id == user_id)
            .order_by(AgentUsage.created_at.desc(), AgentUsage.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items: list[UsageLog] = []
    for usage, agent_name in rows:
        item = UsageLog.model_validate(usage)
        item.agent_id = usage.agent_id
        item.agent_name = agent_name
        items.append(item)

    return {
        "summary": UsageSummary(
            total_requests=int(total_requests),
            total_input_tokens=int(total_input),
            total_output_tokens=int(total_output),
            total_tokens=int(total_tokens),
            series=[],
            countries=[],
        ),
        "items": items,
        "total": int(total_requests),
        "page": page,
        "page_size": page_size,
        "pages": max(1, (int(total_requests) + page_size - 1) // page_size),
    }
