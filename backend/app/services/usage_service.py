"""Usage analytics for the dashboard Usage tab.

One `agent_usage` row is written per chat request (run) by
`agent_session_service` when the run terminates. This module reads that data
back: totals + per-day time series (for the two charts) and a paginated
history list.
"""
import asyncio
import datetime as dt
from typing import Any

from sqlalchemy import Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import AgentUsage
from ..schemas import UsageCountry, UsagePoint, UsageSummary
from .geo import resolve_country

# Default aggregation window for the charts (calendar days, today included).
DEFAULT_DAYS = 30
MAX_DAYS = 90
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

# In-flight fire-and-forget usage writes. The event loop only keeps weak
# references to tasks, so we hold a strong ref here until each write finishes.
_pending_tasks: set[asyncio.Task] = set()


def spawn_usage_log(
    agent_id: int,
    thread_key: str,
    user_id: int | None,
    status: str,
    usage: dict,
    client_ip: str | None = None,
    page_url: str | None = None,
) -> None:
    """Persist a usage row in a detached background task (fire-and-forget).

    The chat run's own db session is closed as soon as the run coroutine
    exits, so the log task opens its own session. The client's country is
    resolved here (outside the run), so geo lookup adds zero latency to chat.
    The task is never awaited and never raises, so logging can neither slow
    down nor break the chat — the run coroutine returns right after the
    terminal lifecycle event.
    """

    async def _write() -> None:
        db = async_session()
        try:
            country = resolve_country(client_ip)
            await record_usage(
                db,
                agent_id,
                thread_key,
                user_id,
                status,
                usage,
                country=country,
                page_url=page_url,
            )
        except Exception:
            try:
                await db.rollback()
            except Exception:
                pass
        finally:
            await db.close()

    task = asyncio.create_task(_write())
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)


async def drain_usage_logs() -> None:
    """Wait for all in-flight usage writes (used by tests at teardown)."""
    if not _pending_tasks:
        return
    await asyncio.gather(*list(_pending_tasks), return_exceptions=True)


async def record_usage(
    db: AsyncSession,
    agent_id: int,
    thread_key: str,
    user_id: int | None,
    status: str,
    usage: dict,
    country: str | None = None,
    page_url: str | None = None,
) -> None:
    """Persist one usage row for a finished run (never raises).

    Usage logging must never break the chat runtime, so any DB error is
    swallowed (rolled back) and the run proceeds normally.
    """
    try:
        db.add(
            AgentUsage(
                agent_id=agent_id,
                channel="widget" if user_id is None else "preview",
                thread_id=thread_key,
                model=(usage.get("model") or None) if isinstance(usage, dict) else None,
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                cost=usage.get("cost"),
                country=country,
                page_url=page_url,
                status=status,
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()


async def get_usage_summary(db: AsyncSession, agent_id: int, days: int) -> UsageSummary:
    """Totals + per-day series for the request / token charts.

    Days with no requests are zero-filled so the charts stay continuous.
    """
    days = max(1, min(days, MAX_DAYS))
    # created_at is a naive TIMESTAMP whose wall-clock is written by the DB
    # server_default (func.now()) in the DB session timezone (e.g.
    # Asia/Jakarta). Keep the window in the same local wall-clock so day
    # bucketing (date_trunc, also session-tz) matches the stored values.
    since = dt.datetime.now().replace(microsecond=0) - dt.timedelta(days=days - 1)

    totals = (
        await db.execute(
            select(
                func.count(AgentUsage.id),
                func.coalesce(func.sum(AgentUsage.input_tokens), 0),
                func.coalesce(func.sum(AgentUsage.output_tokens), 0),
                func.coalesce(func.sum(AgentUsage.total_tokens), 0),
            ).where(AgentUsage.agent_id == agent_id)
        )
    ).one()
    total_requests, total_input, total_output, total_tokens = totals

    rows = (
        await db.execute(
            select(
                # date_trunc('day', …) buckets in the DB session timezone,
                # matching the wall-clock used by func.now() at write time.
                func.date_trunc("day", AgentUsage.created_at).cast(Date).label("day"),
                func.count(AgentUsage.id),
                func.coalesce(func.sum(AgentUsage.input_tokens), 0),
                func.coalesce(func.sum(AgentUsage.output_tokens), 0),
            )
            .where(
                AgentUsage.agent_id == agent_id,
                AgentUsage.created_at >= since,
            )
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

    country_rows = (
        await db.execute(
            select(AgentUsage.country, func.count(AgentUsage.id))
            .where(AgentUsage.agent_id == agent_id, AgentUsage.country.isnot(None))
            .group_by(AgentUsage.country)
            .order_by(func.count(AgentUsage.id).desc())
            .limit(8)
        )
    ).all()
    countries = [
        UsageCountry(country=str(row[0]), requests=int(row[1])) for row in country_rows
    ]

    return UsageSummary(
        total_requests=int(total_requests),
        total_input_tokens=int(total_input),
        total_output_tokens=int(total_output),
        total_tokens=int(total_tokens),
        series=series,
        countries=countries,
    )


async def get_usage_history(
    db: AsyncSession, agent_id: int, page: int, page_size: int
) -> dict[str, Any]:
    """Paginated usage history (newest first)."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    total = (
        await db.execute(
            select(func.count(AgentUsage.id)).where(AgentUsage.agent_id == agent_id)
        )
    ).scalar_one()

    rows = (
        await db.execute(
            select(AgentUsage)
            .where(AgentUsage.agent_id == agent_id)
            .order_by(AgentUsage.created_at.desc(), AgentUsage.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        "items": rows,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "pages": max(1, (int(total) + page_size - 1) // page_size),
    }
