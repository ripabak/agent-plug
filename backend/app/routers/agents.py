"""Agent CRUD + personalization routes (user-scoped)."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Agent, User
from ..rag import store_manager
from ..schemas import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    EmbedResponse,
    UsageResponse,
)
from ..services.embed import build_embed_snippet
from ..services.usage_service import (
    DEFAULT_DAYS,
    DEFAULT_PAGE_SIZE,
    get_usage_history,
    get_usage_summary,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


async def _get_owned_agent(db: AsyncSession, agent_id: int, user: User) -> Agent:
    """Load an agent and ensure it belongs to the user (404 otherwise)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(data: AgentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create an agent; generates its public token automatically."""
    agent = Agent(
        user_id=user.id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        welcome_message=data.welcome_message,
        theme_color=data.theme_color,
        avatar_emoji=data.avatar_emoji,
        chat_theme=data.chat_theme,
        show_thinking=data.show_thinking,
        show_tools=data.show_tools,
        public_token=secrets.token_urlsafe(32),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("", response_model=list[AgentResponse])
async def list_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List the current user's agents (newest first)."""
    result = await db.execute(
        select(Agent).where(Agent.user_id == user.id).order_by(Agent.created_at.desc())
    )
    return [AgentResponse.model_validate(a) for a in result.scalars().all()]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = await _get_owned_agent(db, agent_id, user)
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partial update of personalization fields."""
    agent = await _get_owned_agent(db, agent_id, user)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete an agent, its sources (DB cascade) and its in-memory index."""
    agent = await _get_owned_agent(db, agent_id, user)
    await db.delete(agent)
    await db.commit()
    store_manager.delete_agent(agent_id)


@router.post("/{agent_id}/regenerate-token", response_model=AgentResponse)
async def regenerate_token(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Rotate the public token (old widget snippets stop working)."""
    agent = await _get_owned_agent(db, agent_id, user)
    agent.public_token = secrets.token_urlsafe(32)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}/embed", response_model=EmbedResponse)
async def get_embed_snippet(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the HTML snippet to paste into an external website."""
    agent = await _get_owned_agent(db, agent_id, user)
    return EmbedResponse(html=build_embed_snippet(agent), agent_id=agent.id, public_token=agent.public_token)


@router.get("/{agent_id}/usage", response_model=UsageResponse)
async def get_usage(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = DEFAULT_DAYS,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
):
    """Usage dashboard data: totals + daily series + paginated history."""
    await _get_owned_agent(db, agent_id, user)
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
