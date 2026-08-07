"""Agent session runtime: background runs + SSE event streaming.

Each thread key maps to an AgentSession that buffers events and fans them out
to SSE subscribers, so the stream endpoint can reconnect via the `since` seq.
"""
import asyncio
import json
import re
import uuid
from collections import defaultdict
from urllib.parse import urlparse
from typing import AsyncGenerator, Optional

from langchain.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select

from ..agent.agent import build_agent
from ..agent.checkpointer import get_checkpointer
from ..agent.tools import reset_progress_emitter, set_progress_emitter
from ..database import async_session
from ..models import AgentThread
from .usage_service import spawn_usage_log

# Matches the source markers embedded in RAG tool outputs:
#   [Source: https://example.com | Page Title]
#   [Source: file://12/abc.pdf | document]
#   [Source: text://abc123 | My Notes]
_SOURCE_MARKER_RE = re.compile(r"\[Source:\s*((?:https?|file|text)://[^\s|\]]+)(?:\s*\|\s*([^\]]*))?\]")


def _is_sane_http_url(url: str) -> bool:
    """True only for well-formed public http(s) URLs (rejects model glitches
    like repeated schemes / mangled hosts)."""
    if not url.startswith(("http://", "https://")):
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    netloc = parsed.netloc
    if "://" in netloc or "/" in netloc:
        return False
    host = netloc.rsplit(":", 1)[0]  # strip optional port
    return bool(host) and "." in host and not host.startswith(".") and not host.endswith(".")


def _is_sane_source_url(url: str) -> bool:
    """Accept http(s) URLs, local `file://` (PDFs) and `text://` (pasted text)."""
    if url.startswith("file://"):
        path = url[len("file://"):]
        return bool(path) and "/" in path and ".." not in path
    if url.startswith("text://"):
        return len(url) > len("text://")
    return _is_sane_http_url(url)


def parse_source_markers(text: str) -> list[dict]:
    """Extract {url, title} pairs from [Source: ...] markers in a text.

    Only well-formed http(s) URLs are kept (defense against malformed URLs
    that the model may produce in its own output).
    """
    found: list[dict] = []
    for m in _SOURCE_MARKER_RE.finditer(text or ""):
        url = m.group(1)
        if not _is_sane_source_url(url):
            continue
        title = (m.group(2) or url).strip()
        found.append({"url": url, "title": title})
    return found


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for s in sources:
        if s["url"] not in seen:
            seen.add(s["url"])
            out.append(s)
    return out


class AgentSession:
    """Buffers events for one thread and fans them out to subscribers."""

    def __init__(self) -> None:
        self.run_id: str | None = None
        self.events: list[dict] = []
        self.subscribers: list[asyncio.Queue] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._seq = 0
        self.total_usage: dict = {}

    def buffer_event(self, event: dict) -> None:
        self._seq += 1
        event["seq"] = self._seq
        if "event_id" not in event:
            event["event_id"] = str(uuid.uuid4())
        event["run_id"] = self.run_id
        self.events.append(event)
        for q in self.subscribers:
            q.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self.subscribers:
            self.subscribers.remove(q)

    def get_events_since(self, since: int, channels: list[str]) -> list[dict]:
        result = []
        for event in self.events:
            seq = event.get("seq", 0)
            method = event.get("method", "")
            if seq > since and (method in channels or "*" in channels):
                result.append(event)
        return result


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, AgentSession] = defaultdict(AgentSession)

    def get(self, thread_id: str) -> AgentSession:
        return self._sessions[thread_id]

    def remove(self, thread_id: str) -> None:
        self._sessions.pop(thread_id, None)


session_manager = SessionManager()


async def drain_run_tasks() -> None:
    """Wait for all background agent runs to terminate (test teardown).

    Run coroutines may spawn fire-and-forget usage logs in their terminal
    handlers, so call this BEFORE draining the usage log tasks.
    """
    for session in list(session_manager._sessions.values()):
        task = session._task
        if task is not None and not task.done():
            await asyncio.gather(task, return_exceptions=True)


def stop_agent_run(thread_id: str) -> None:
    """Cancel the running task for a thread, if any."""
    session = session_manager.get(thread_id)
    if session._task and not session._task.done():
        session._task.cancel()


def _make_event(method: str, data) -> dict:
    return {"method": method, "params": {"data": data}}


def _to_langchain_messages(messages: list[dict]) -> list:
    """Convert [{role, content}] chat messages to LangChain messages.

    Keeps only the last message as input when there is prior history
    (handled by caller); here we convert all provided ones.
    """
    result = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role in ("assistant", "ai"):
            result.append(AIMessage(content=content))
        else:
            result.append(HumanMessage(content=content))
    return result


async def start_agent_run(
    thread_key: str,
    agent_id: int,
    messages: list[dict],
    user_id: int | None = None,
    client_ip: str | None = None,
    page_url: str | None = None,
) -> str:
    """Start an agent run in the background; returns a run_id."""
    session = session_manager.get(thread_key)
    run_id = str(uuid.uuid4())
    session.run_id = run_id
    session._running = True
    session.events.clear()
    session.total_usage = {}

    async def run() -> None:
        db = async_session()
        try:
            agent = await build_agent(db, agent_id, get_checkpointer())
            thread_config: RunnableConfig = {"configurable": {"thread_id": thread_key}}

            await _upsert_thread_mapping(db, thread_key, agent_id, user_id, page_url)

            state = await agent.aget_state(thread_config)
            has_history = bool(state is not None and state.values.get("messages"))
            input_messages = (
                _to_langchain_messages(messages[-1:]) if has_history and messages else _to_langchain_messages(messages)
            )

            stream = await agent.astream_events(
                {"messages": input_messages},
                config=thread_config,
                version="v3",
            )

            session.buffer_event(_make_event("lifecycle", {"event": "running"}))

            current_msg_id: Optional[str] = None
            last_tool_call_id = ""
            # Sources retrieved by RAG tools in this run (resolved server-side
            # from tool outputs, so links never come from model-generated URLs).
            run_sources: list[dict] = []

            def on_tool_progress(message: str) -> None:
                session.buffer_event(
                    _make_event("tool_progress", {"tool_call_id": last_tool_call_id, "message": message})
                )

            set_progress_emitter(on_tool_progress)

            async for event in stream:
                method = event.get("method", "")
                params = event.get("params", {}) or {}
                raw_data = params.get("data", {})

                if method == "messages":
                    msg_event = raw_data[0] if isinstance(raw_data, tuple) else raw_data
                    if isinstance(msg_event, str):
                        continue
                    ev_type = msg_event.get("event", "")

                    if ev_type == "message-start":
                        current_msg_id = str(uuid.uuid4())
                        session.buffer_event(
                            _make_event("message_start", {"id": current_msg_id, "role": "assistant"})
                        )
                    elif ev_type == "content-block-delta":
                        delta = msg_event.get("delta", {})
                        if not current_msg_id:
                            continue
                        if delta.get("type") == "reasoning-delta" and delta.get("reasoning"):
                            session.buffer_event(
                                _make_event(
                                    "text_delta",
                                    {"id": current_msg_id, "delta": delta["reasoning"], "kind": "reasoning"},
                                )
                            )
                        elif delta.get("type") == "text-delta" and delta.get("text"):
                            session.buffer_event(
                                _make_event(
                                    "text_delta",
                                    {"id": current_msg_id, "delta": delta["text"], "kind": "text"},
                                )
                            )
                    elif ev_type == "message-finish":
                        if current_msg_id:
                            usage = msg_event.get("usage") or {}
                            metadata = msg_event.get("metadata") or {}
                            for k in ("input_tokens", "output_tokens", "total_tokens"):
                                session.total_usage[k] = session.total_usage.get(k, 0) + usage.get(k, 0)
                            session.total_usage["calls"] = session.total_usage.get("calls", 0) + 1
                            # Keep the last model + cost for the usage dashboard row.
                            session.total_usage["model"] = metadata.get("model_name")
                            session.total_usage["cost"] = metadata.get("cost")
                            session.buffer_event(
                                _make_event(
                                    "message_end",
                                    {
                                        "id": current_msg_id,
                                        "usage": {
                                            "input_tokens": usage.get("input_tokens", 0),
                                            "output_tokens": usage.get("output_tokens", 0),
                                            "total_tokens": usage.get("total_tokens", 0),
                                            "cost": metadata.get("cost"),
                                        },
                                        "total_usage": session.total_usage.copy(),
                                        "model": metadata.get("model_name"),
                                    },
                                )
                            )
                            # Structured source list for this assistant message
                            # (resolved from real tool outputs, not LLM text).
                            if run_sources:
                                session.buffer_event(
                                    _make_event(
                                        "sources",
                                        {"id": current_msg_id, "sources": list(run_sources)},
                                    )
                                )

                elif method == "tools":
                    ev_type = raw_data.get("event", "")

                    if ev_type == "tool-started":
                        last_tool_call_id = raw_data.get("tool_call_id", "")
                        session.buffer_event(
                            _make_event(
                                "tool_start",
                                {
                                    "tool_call_id": last_tool_call_id,
                                    "name": raw_data.get("tool_name", ""),
                                    "args": raw_data.get("input", {}),
                                },
                            )
                        )
                    elif ev_type == "tool-finished":
                        tc_id = raw_data.get("tool_call_id", "")
                        output = raw_data.get("output", "")
                        # Harvest exact source URLs from the tool output (they
                        # were copied from the vector store metadata).
                        run_sources = _dedupe_sources(run_sources + parse_source_markers(str(output)))
                        session.buffer_event(
                            _make_event(
                                "tool_end",
                                {"tool_call_id": tc_id, "output": str(output) if output else "", "error": None},
                            )
                        )

            session.buffer_event(
                _make_event("lifecycle", {"event": "completed", "total_usage": session.total_usage.copy()})
            )
            spawn_usage_log(agent_id, thread_key, user_id, "completed", session.total_usage.copy(), client_ip)

        except asyncio.CancelledError:
            session.buffer_event(_make_event("lifecycle", {"event": "cancelled"}))
            spawn_usage_log(agent_id, thread_key, user_id, "cancelled", session.total_usage.copy(), client_ip)
        except Exception as exc:  # surface failures to the stream
            session.buffer_event(_make_event("lifecycle", {"event": "failed", "error": str(exc)}))
            spawn_usage_log(agent_id, thread_key, user_id, "failed", session.total_usage.copy(), client_ip)
        finally:
            reset_progress_emitter()
            session._running = False
            await db.close()

    session._task = asyncio.create_task(run())
    return run_id


def _is_terminal_event(event: dict) -> bool:
    """True for the lifecycle event that ends a run (completed/failed/cancelled)."""
    if event.get("method") != "lifecycle":
        return False
    data = (event.get("params") or {}).get("data") or {}
    return data.get("event") in ("completed", "failed", "cancelled")


async def stream_events(
    thread_id: str,
    channels: list[str],
    since: int = 0,
) -> AsyncGenerator[str, None]:
    """SSE generator: replay buffered events then live events from subscribers.

    The stream closes right after the terminal lifecycle event (completed /
    failed / cancelled) is delivered, so clients can detect the end of a run
    instead of hanging on keep-alives forever.
    """
    session = session_manager.get(thread_id)
    q = session.subscribe()
    terminal = False
    try:
        for event in session.get_events_since(since, channels):
            yield _encode_sse(event)
            if _is_terminal_event(event):
                terminal = True
        while not terminal:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            if event["method"] in channels or "*" in channels:
                yield _encode_sse(event)
                if _is_terminal_event(event):
                    terminal = True
    finally:
        session.unsubscribe(q)


def _encode_sse(event: dict) -> str:
    """Encode a buffered event dict into an SSE frame."""
    event_id = event.get("event_id", "")
    id_line = f"id: {event_id}\n" if event_id else ""
    event_type = event.get("method", "message")
    data = json.dumps({k: v for k, v in event.items() if k not in ("seq",)})
    return f"{id_line}event: {event_type}\ndata: {data}\n\n"


async def _upsert_thread_mapping(
    db, thread_key: str, agent_id: int, user_id: int | None, page_url: str | None = None
) -> None:
    result = await db.execute(select(AgentThread).where(AgentThread.thread_id == thread_key))
    mapping = result.scalar_one_or_none()
    if mapping is None:
        db.add(AgentThread(thread_id=thread_key, agent_id=agent_id, user_id=user_id, page_url=page_url))
    elif mapping.agent_id != agent_id:
        mapping.agent_id = agent_id
        mapping.user_id = user_id
        mapping.page_url = page_url
    elif page_url is not None:
        mapping.page_url = page_url  # SPA navigation: keep the URL current
    await db.commit()


def _msg_content(content) -> str:
    """Extract plain text from a message's content (str or content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    text_parts.append(block["text"])
                elif block.get("type") == "reasoning" and block.get("reasoning"):
                    text_parts.append(block["reasoning"])
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts)
    return str(content)


def serialize_message(message) -> dict:
    """Serialize a LangChain message to the client-facing JSON shape."""
    mtype = message.type
    content = _msg_content(message.content)
    if mtype == "human":
        return {"type": "human", "content": content}
    if mtype == "ai":
        result: dict = {"type": "ai", "content": content}
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            result["tool_calls"] = [
                {"id": tc.get("id", ""), "name": tc.get("name", ""), "args": tc.get("args", {})}
                for tc in tool_calls
            ]
        return result
    return {"type": mtype, "content": content}


async def get_thread_history(thread_key: str) -> list[dict]:
    """Return serialized messages for a thread from the checkpointer."""
    agent = await build_agent_from_thread(thread_key)
    if agent is None:
        return []
    state = await agent.aget_state({"configurable": {"thread_id": thread_key}})
    messages = (state.values.get("messages") or []) if state is not None else []
    return [serialize_message(m) for m in messages]


async def build_agent_from_thread(thread_key: str):
    """Load the agent id for a thread and build its graph (or None)."""
    async with async_session() as db:
        mapping = (
            await db.execute(select(AgentThread).where(AgentThread.thread_id == thread_key))
        ).scalar_one_or_none()
        if mapping is None:
            return None
        agent_id = mapping.agent_id
    db = async_session()
    try:
        return await build_agent(db, agent_id, get_checkpointer())
    finally:
        await db.close()


async def delete_thread_state(thread_key: str) -> None:
    """Delete checkpointer state for a thread (mapping deleted by caller)."""
    await get_checkpointer().adelete_thread(thread_key)
