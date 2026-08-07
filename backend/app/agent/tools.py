"""Agent tools: the RAG retrieval tool bound to a specific agent's vector store."""
from typing import Callable, Optional

from langchain.tools import tool
from langchain_core.vectorstores import VectorStore

from ..config import RAG_TOP_K
from ..rag import store_manager

# Namespace to pass progress messages out of tools to the SSE stream.
_PROGRESS_EMITTER: Optional[Callable[[str], None]] = None


def set_progress_emitter(fn: Optional[Callable[[str], None]]) -> None:
    """Install (or clear) the current run's progress emitter."""
    global _PROGRESS_EMITTER
    _PROGRESS_EMITTER = fn


def reset_progress_emitter() -> None:
    """Clear the progress emitter after a run ends."""
    global _PROGRESS_EMITTER
    _PROGRESS_EMITTER = None


def emit_progress(message: str) -> None:
    """Forward a tool progress message to the active SSE session (if any)."""
    if _PROGRESS_EMITTER is not None:
        _PROGRESS_EMITTER(message)


def format_docs(docs) -> str:
    """Format retrieved chunks with their source URL + title for the model."""
    lines: list[str] = []
    for doc in docs:
        meta = doc.metadata or {}
        source = f"[Source: {meta.get('url', '?')}"
        if meta.get("title"):
            source += f" | {meta['title']}"
        source += "]"
        lines.append(f"{source}\n{doc.page_content}")
    return "\n\n".join(lines)


def create_rag_tool(agent_id: int, store: VectorStore | None = None, top_k: int = RAG_TOP_K):
    """Build the `search_knowledge_base` tool for an agent.

    `store` is optional; when omitted the tool looks up the agent's store via
    the global manager at call time (keeps the tool valid across re-indexes).
    """

    @tool
    async def search_knowledge_base(query: str) -> str:
        """Search the website's knowledge base for information relevant to the question.

        Use this first for any question about the website, product, services,
        pricing, policies, docs, or FAQ. Returns matching content snippets,
        each prefixed with its source URL. If nothing relevant is found, the
        function clearly says so.

        Args:
            query: A focused search query describing the information needed.
        """
        emit_progress("Searching the knowledge base…")
        if store is not None:
            docs = await store.asimilarity_search(query, k=top_k)
        else:
            docs = await store_manager.asearch(agent_id, query, k=top_k)

        if not docs:
            return (
                "No relevant content found in the knowledge base for this query. "
                "Do not invent website-specific facts."
            )
        return (
            f"Found {len(docs)} relevant snippet(s) from the knowledge base:\n\n"
            + format_docs(docs)
        )

    return search_knowledge_base
