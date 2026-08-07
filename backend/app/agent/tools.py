"""Agent tools: the RAG retrieval tool + current-page context tool."""
import asyncio
import ipaddress
import socket
import time
from typing import Callable, Optional
from urllib.parse import urlparse

from langchain.tools import tool
from langchain_core.runnables.config import RunnableConfig
from langchain_core.vectorstores import VectorStore
from sqlalchemy import select

from ..config import PAGE_CONTEXT_MAX_CHARS, RAG_TOP_K
from ..database import async_session
from ..models import AgentThread
from ..rag import store_manager
from ..rag.fetcher import fetch_page

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


# ---------------------------------------------------------------------------
# read_current_page — live content of the page the visitor is currently viewing
# ---------------------------------------------------------------------------
# The widget reports `window.location.href` on every run.start; it's stored on
# the thread (AgentThread.page_url) and this tool fetches it on demand. Only
# called when the visitor asks about the current page (tool description gates
# the model). Fetches run server-side, so the URL is SSRF-guarded (untrusted).

# Cache: {page_url -> (fetched_at, title, text)} — follow-up questions in a
# thread don't refetch the same page on every turn. Bounded + TTL'd.
_PAGE_CACHE: dict[str, tuple[float, str, str]] = {}
_PAGE_CACHE_TTL = 120.0  # seconds
_PAGE_CACHE_MAX = 500


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _is_blocked_host(url: str) -> bool:
    """SSRF guard: reject URLs whose host is a private/loopback/link-local IP.

    The page_url arrives from the public widget (untrusted), so the backend
    must never fetch internal addresses (metadata IPs, localhost, LAN).
    """
    host = urlparse(url).hostname
    if not host:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        return _is_blocked_ip(ip)
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return True  # unresolvable — treat as blocked so the fetch fails cleanly
    return any(_is_blocked_ip(ipaddress.ip_address(info[4][0])) for info in infos)


def _normalize_url(raw: str) -> str:
    """Normalize a model-provided URL: trim, default to https:// when no scheme."""
    url = (raw or "").strip()
    if not url:
        raise ValueError("URL is empty")
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("must be an absolute http(s) URL")
    return url


def _fetch_page_text(page_url: str) -> tuple[str, str]:
    """Sync fetch with SSRF guard + TTL cache (run via asyncio.to_thread)."""
    now = time.monotonic()
    cached = _PAGE_CACHE.get(page_url)
    if cached and now - cached[0] < _PAGE_CACHE_TTL:
        return cached[1], cached[2]
    if _is_blocked_host(page_url):
        raise ValueError("URL resolves to a non-public address")
    page = fetch_page(page_url)
    if len(_PAGE_CACHE) >= _PAGE_CACHE_MAX:
        _PAGE_CACHE.clear()
    _PAGE_CACHE[page_url] = (now, page.title, page.text)
    return page.title, page.text


def _format_page_output(url: str, title: str, text: str) -> str:
    """Truncate page text to PAGE_CONTEXT_MAX_CHARS and add the source marker
    (renders a source chip in the widget, like RAG citations)."""
    max_chars = PAGE_CONTEXT_MAX_CHARS
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " …"
    return "[Source: " + url + " | " + (title or "Current page") + "]\n" + text


def create_page_tool(agent_id: int):
    """Build the `read_current_page` tool for an agent.

    The page URL comes from the thread the run is executing on (the widget
    reports it with every message), never from the model — so the model can't
    point the server at arbitrary URLs (SSRF). The tool takes no arguments.
    """

    @tool
    async def read_current_page(config: RunnableConfig) -> str:
        """Read the content of the web page the visitor is currently viewing.

        Use ONLY when the visitor asks about the content of the page they are
        currently on (e.g. "what does this page say about X?", "summarize this
        page", "is this offer in the page?"). For questions about the website
        in general, use search_knowledge_base instead. Returns the page title
        followed by its readable text.
        """
        thread_key = (config.get("configurable") or {}).get("thread_id", "")
        if not thread_key:
            return "No current page context is available for this conversation."
        async with async_session() as db:
            mapping = (
                await db.execute(select(AgentThread).where(AgentThread.thread_id == thread_key))
            ).scalar_one_or_none()
            page_url = mapping.page_url if mapping else None
        if not page_url:
            return (
                "No current page context is available for this conversation. "
                "Answer from the knowledge base instead."
            )
        emit_progress("Reading the current page…")
        try:
            title, text = await asyncio.to_thread(_fetch_page_text, page_url)
        except Exception as exc:
            return f"Could not read the current page ({page_url}): {exc}"
        return _format_page_output(page_url, title, text)

    return read_current_page


def create_fetch_web_tool():
    """Build the `fetch_web_page` tool.

    The URL is chosen BY THE MODEL (from the visitor's question), so it is
    fully SSRF-guarded — private/loopback/link-local addresses are refused.
    """

    @tool
    async def fetch_web_page(url: str) -> str:
        """Fetch and read the content of any public web page by URL.

        Use when the visitor asks about a specific web page that is NOT in the
        knowledge base (e.g. "what does example.com say about X?", "check the
        latest info at <url>", "summarize <url>"). For the page the visitor is
        currently viewing, use read_current_page instead. Returns the page
        title followed by its readable text (truncated). Only public http(s)
        URLs can be fetched — internal/private addresses are refused.
        """
        emit_progress("Fetching web page…")
        try:
            target = _normalize_url(url)
            title, text = await asyncio.to_thread(_fetch_page_text, target)
        except Exception as exc:
            return f"Could not fetch {url.strip() or '(empty URL)'}: {exc}"
        return _format_page_output(target, title, text)

    return fetch_web_page
