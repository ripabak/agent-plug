"""Read-only admin endpoints: platform stats, user monitoring.

The admin is a special principal configured via env (ADMIN_EMAIL /
ADMIN_PASSWORD) — NOT a User row. Every endpoint here is GET-only; the admin
can monitor users/agents/usage but never mutate anything.
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..auth import create_admin_token, get_current_admin
from ..database import get_db
from ..schemas import (
    AdminAgentDetail,
    AdminLogin,
    AdminStats,
    AdminTokenResponse,
    AdminUserDetail,
    AdminUsersResponse,
    EmbedResponse,
    SourceResponse,
    UsageResponse,
)
from ..services import admin_service
from ..services.embed import build_embed_snippet
from ..services.usage_service import DEFAULT_PAGE_SIZE, get_usage_history, get_usage_summary

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(data: AdminLogin):
    """Log in as the platform admin (email/password from env)."""
    if not config.ADMIN_EMAIL or not config.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is not configured",
        )
    email_ok = secrets.compare_digest(data.email, config.ADMIN_EMAIL)
    pwd_ok = secrets.compare_digest(data.password, config.ADMIN_PASSWORD)
    if not email_ok or not pwd_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return AdminTokenResponse(
        access_token=create_admin_token(), email=config.ADMIN_EMAIL
    )


@router.get("/me")
async def admin_me(_email: str = Depends(get_current_admin)):
    """Session restore for the admin (returns the admin email)."""
    return {"email": config.ADMIN_EMAIL}


@router.get("/stats", response_model=AdminStats)
async def admin_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Platform-wide totals (all time) + daily series for the charts."""
    return await admin_service.get_admin_stats(db, days)


@router.get("/users", response_model=AdminUsersResponse)
async def admin_users(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Paginated user list with per-user aggregates; search by email/name."""
    return await admin_service.list_users(db, q=q, page=page, page_size=page_size)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def admin_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Read-only view of one user: profile + their agents (with stats)."""
    result = await admin_service.get_user_detail(db, user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return result


@router.get("/users/{user_id}/usage", response_model=UsageResponse)
async def admin_user_usage(
    user_id: int,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Paginated usage history across all agents of one user + totals."""
    return await admin_service.get_user_usage(db, user_id, page, page_size)


async def _load_agent_or_404(db: AsyncSession, agent_id: int):
    agent = await admin_service.get_agent_or_none(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.get("/agents/{agent_id}", response_model=AdminAgentDetail)
async def admin_agent_detail(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Read-only view of one agent (any user) + its owner."""
    result = await admin_service.get_agent_detail(db, agent_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return result


@router.get("/agents/{agent_id}/sources", response_model=list[SourceResponse])
async def admin_agent_sources(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Read-only knowledge sources of one agent."""
    await _load_agent_or_404(db, agent_id)
    return await admin_service.get_agent_sources(db, agent_id)


@router.get("/agents/{agent_id}/usage", response_model=UsageResponse)
async def admin_agent_usage(
    agent_id: int,
    days: int = 30,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Usage dashboard data (charts + history) for one agent, admin-scoped."""
    await _load_agent_or_404(db, agent_id)
    summary = await get_usage_summary(db, agent_id, days)
    history = await get_usage_history(db, agent_id, page, page_size)
    return UsageResponse(
        summary=summary,
        items=history["items"],
        total=history["total"],
        page=history["page"],
        page_size=history["page_size"],
        pages=history["pages"],
    )


@router.get("/agents/{agent_id}/embed", response_model=EmbedResponse)
async def admin_agent_embed(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    _email: str = Depends(get_current_admin),
):
    """Embed snippet for one agent (read-only view)."""
    agent = await _load_agent_or_404(db, agent_id)
    return EmbedResponse(
        html=build_embed_snippet(agent), agent_id=agent.id, public_token=agent.public_token
    )
