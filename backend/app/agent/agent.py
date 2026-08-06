"""Agent builder: creates the Deep-Agents `create_agent` graph per agent.

Combines ChatOpenRouter + middleware + AsyncPostgresSaver with the agent's
personalized system prompt and the RAG retrieval tool wired to its in-memory
vector store.
"""
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    SummarizationMiddleware,
)
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AGENT_SYSTEM_PROMPT, OPENROUTER_MODEL
from ..models import Agent
from .tools import create_rag_tool


def build_system_prompt(agent: Agent) -> str:
    """Compose the personalized system prompt for an agent."""
    description = agent.description or f"an AI assistant on the {agent.name} website"
    return AGENT_SYSTEM_PROMPT.format(name=agent.name, description=description)


async def build_agent(
    db: AsyncSession,
    agent_id: int,
    checkpointer: AsyncPostgresSaver,
):
    """Build a compiled agent graph for the given agent id.

    Returns the compiled graph object (CompiledStateGraph); typed loosely to
    avoid a hard dependency in the caller's tests.
    """
    agent = (
        await db.execute(select(Agent).where(Agent.id == agent_id))
    ).scalar_one_or_none()
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found")

    model = ChatOpenRouter(
        model=OPENROUTER_MODEL,
        temperature=0.3,
        max_tokens=8192,
        reasoning={"effort": "low", "summary": "auto"},
    )

    return create_agent(
        model=model,
        tools=[create_rag_tool(agent.id)],
        system_prompt=build_system_prompt(agent),
        checkpointer=checkpointer,
        middleware=[
            SummarizationMiddleware(
                model=model,
                trigger=("tokens", 80000),
                keep=("messages", 10),
            ),
            ContextEditingMiddleware(
                edits=[
                    ClearToolUsesEdit(
                        trigger=60000,
                        keep=5,
                        clear_tool_inputs=True,
                    ),
                ],
            ),
        ],
    )
