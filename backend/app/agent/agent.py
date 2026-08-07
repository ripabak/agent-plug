"""Agent builder: creates the Deep-Agents `create_agent` graph per agent.

Combines ChatOpenRouter + middleware + AsyncPostgresSaver with the agent's
personalized system prompt and the RAG retrieval tool wired to its in-memory
vector store.
"""
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import (
    AGENT_SYSTEM_PROMPT,
    OPENROUTER_FALLBACK_MODELS,
    OPENROUTER_MODEL,
)
from ..models import Agent
from .tools import create_rag_tool


def _build_model(model_id: str) -> ChatOpenRouter:
    """Construct a ChatOpenRouter with the project's shared model params."""
    return ChatOpenRouter(
        model=model_id,
        temperature=0.3,
        max_tokens=8192,
        reasoning={"effort": "low", "summary": "auto"},
    )


def build_system_prompt(agent: Agent) -> str:
    """Compose the personalized system prompt for an agent.

    The base prompt (knowledge base + citation rules) always stays intact;
    an optional persona prompt (dashboard "Agent personality" templates) is
    appended as ADDITIVE instructions and never replaces the base.
    """
    description = agent.description or f"an AI assistant on the {agent.name} website"
    prompt = AGENT_SYSTEM_PROMPT.format(name=agent.name, description=description)
    if agent.persona_prompt and agent.persona_prompt.strip():
        prompt += f"\n\n## Persona\n{agent.persona_prompt.strip()}"
    return prompt


def build_middleware(model: ChatOpenRouter) -> list:
    """Build the agent middleware chain (in execution order).

    Order matters: model fallback wraps the whole run so a primary-model
    failure/rate-limit transparently falls through to the configured
    alternates; per-run cost guards (model + tool call limits) prevent a
    runaway widget visitor from racking up unbounded tokens; tool retry
    absorbs transient pgvector/db errors; summarization + context editing
    keep long conversations inside the model's context window.
    """
    fallback_models = [
        _build_model(m)
        for m in (x.strip() for x in OPENROUTER_FALLBACK_MODELS.split(","))
        if m
    ]
    fallback_chain = [ModelFallbackMiddleware(model, *fallback_models)] if fallback_models else []
    return [
        *fallback_chain,
        # End the run gracefully after 5 model calls per run (cost guard).
        ModelCallLimitMiddleware(run_limit=5, exit_behavior="end"),
        # Cap RAG searches per run (a few lookups is enough for any question).
        ToolCallLimitMiddleware(run_limit=5),
        # Absorb transient vector-store/db errors with exponential backoff.
        ToolRetryMiddleware(max_retries=2),
        # Summarize history once the conversation approaches 30k tokens.
        SummarizationMiddleware(
            model=model,
            trigger=("tokens", 30000),
            keep=("messages", 10),
        ),
        # Trim stale tool calls (with inputs) from the context.
        ContextEditingMiddleware(
            edits=[
                ClearToolUsesEdit(
                    trigger=60000,
                    keep=5,
                    clear_tool_inputs=True,
                ),
            ],
        ),
    ]


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

    model = _build_model(OPENROUTER_MODEL)

    return create_agent(
        model=model,
        tools=[create_rag_tool(agent.id)],
        system_prompt=build_system_prompt(agent),
        checkpointer=checkpointer,
        middleware=build_middleware(model),
    )
