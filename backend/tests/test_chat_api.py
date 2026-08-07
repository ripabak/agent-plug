"""Integration tests for the SSE chat runtime (public widget protocol).

The dashboard preview embeds the real widget (`app/widget/widget.js`), so
the ONLY chat path in the platform is the public API (`/api/public/agents/
{id}/commands|stream|history`, token-authenticated). The authed
`/api/threads` router was removed — these tests exercise the public route.

Uses a FAKE agent graph (no real LLM calls) injected by monkeypatching
`app.services.agent_session_service.build_agent`.

NOTE: HTTP-level SSE streaming is not exercised via httpx ASGITransport (it
buffers the full body, which never ends for an SSE stream). Instead the SSE
event contract is tested at the service layer via `stream_events()`, while
the HTTP routes are tested for command handling + auth behavior.
"""
import uuid

import pytest
import httpx

from app.agent.checkpointer import close_checkpointer, init_checkpointer
from app.services import agent_session_service as svc
from app.services.usage_service import drain_usage_logs


class FakeState:
    def __init__(self):
        self.values = {"messages": []}


class FakeAgent:
    """Mimics the compiled graph surface used by start_agent_run."""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.state = FakeState()

    async def aget_state(self, config):
        return self.state

    async def astream_events(self, input, config, version="v3"):
        """Mimic langgraph v3: coroutine returning an async iterator."""

        async def _gen():
            yield {"method": "messages", "params": {"data": ({"event": "message-start"},)}}
            yield {
                "method": "messages",
                "params": {"data": ({"event": "content-block-delta", "delta": {"type": "text-delta", "text": "Hello "}},)},
            }
            yield {
                "method": "messages",
                "params": {"data": ({"event": "content-block-delta", "delta": {"type": "text-delta", "text": "world!"}},)},
            }
            yield {
                "method": "tools",
                "params": {"data": {"event": "tool-started", "tool_call_id": "tc1", "tool_name": "search_knowledge_base", "input": {"query": "x"}}},
            }
            yield {
                "method": "tools",
                "params": {"data": {"event": "tool-finished", "tool_call_id": "tc1", "output": "[Source: https://example.com | Example]\nchunk one\n\n[Source: https://example.com/docs | Docs]\nchunk two"}},
            }
            yield {
                "method": "messages",
                "params": {"data": ({"event": "message-finish", "usage": {"total_tokens": 10}, "metadata": {"model_name": "test-model"}},)},
            }

        return _gen()


@pytest.fixture(autouse=True)
def _fake_agent(monkeypatch):
    async def fake_build_agent(db, agent_id, checkpointer):
        return FakeAgent(agent_id)

    monkeypatch.setattr("app.services.agent_session_service.build_agent", fake_build_agent)


@pytest.fixture()
async def async_client():
    """Async client with ASGITransport; inits the checkpointer on the same loop."""
    await init_checkpointer()
    transport = httpx.ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    # Let background runs finish (they may spawn usage log tasks), then
    # drain the fire-and-forget usage writes before the loop closes, and
    # release the checkpointer's connection pool (loop-affinity).
    await svc.drain_run_tasks()
    await drain_usage_logs()
    await close_checkpointer()


async def _register_and_create_agent(async_client) -> tuple[dict, dict]:
    """Register a user + create an agent; returns (auth_headers, agent)."""
    email = f"chat-{uuid.uuid4().hex}@example.com"
    res = await async_client.post(
        "/api/auth/register",
        json={"email": email, "display_name": "Chat", "password": "secret123"},
    )
    assert res.status_code == 201
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    res = await async_client.post("/api/agents", json={"name": "Chat Bot", "description": "d"}, headers=headers)
    assert res.status_code == 201
    return headers, res.json()


async def _collect_stream(thread_key: str, channels=None) -> str:
    """Consume the SSE generator until the completed lifecycle event."""
    frames = []
    async for frame in svc.stream_events(thread_key, channels or ["*"], 0):
        frames.append(frame)
        if "event: lifecycle" in frame and "completed" in frame:
            break
    return "\n".join(frames)


async def _collect_stream_until_end(thread_key: str, channels=None) -> str:
    """Consume the SSE generator to the END — must terminate on its own.

    Regression guard: the stream must close right after the terminal
    lifecycle event (no infinite keep-alive loop), otherwise the widget
    would keep "streaming" forever.
    """
    frames = []
    async for frame in svc.stream_events(thread_key, channels or ["*"], 0):
        frames.append(frame)
    return "\n".join(frames)


async def _start_public_chat(async_client, agent: dict, thread_id: str, **input_extra) -> None:
    tok = {"X-Agent-Token": agent["public_token"]}
    res = await async_client.post(
        f"/api/public/agents/{agent['id']}/commands",
        json={
            "method": "run.start",
            "id": "c1",
            "params": {"input": {"thread_id": thread_id, "messages": [{"role": "user", "content": "hi"}], **input_extra}},
        },
        headers=tok,
    )
    assert res.status_code == 200
    assert res.json()["type"] == "success"


# --------------------------------------------------------------- HTTP routes
@pytest.mark.asyncio
async def test_run_start_and_cancel_commands(async_client):
    _headers, agent = await _register_and_create_agent(async_client)
    tok = {"X-Agent-Token": agent["public_token"]}

    res = await async_client.post(
        f"/api/public/agents/{agent['id']}/commands",
        json={"method": "run.start", "id": "c1", "params": {"input": {"thread_id": "t1", "messages": [{"role": "user", "content": "hi"}]}}},
        headers=tok,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "success"
    assert body["result"]["run_id"]

    res = await async_client.post(
        f"/api/public/agents/{agent['id']}/commands",
        json={"method": "run.cancel", "id": "c2", "params": {"thread_id": "t1"}},
        headers=tok,
    )
    assert res.json()["result"] == {"cancelled": True}


@pytest.mark.asyncio
async def test_unknown_command(async_client):
    _headers, agent = await _register_and_create_agent(async_client)
    res = await async_client.post(
        f"/api/public/agents/{agent['id']}/commands",
        json={"method": "nope", "id": "c1"},
        headers={"X-Agent-Token": agent["public_token"]},
    )
    assert res.json()["error"] == "unknown_command"


@pytest.mark.asyncio
async def test_public_widget_requires_token(async_client):
    _headers, agent = await _register_and_create_agent(async_client)

    assert (await async_client.get(f"/api/public/agents/{agent['id']}/config")).status_code == 401
    assert (await async_client.post(f"/api/public/agents/{agent['id']}/commands", json={})).status_code == 401
    res = await async_client.get(f"/api/public/agents/{agent['id']}/config", headers={"X-Agent-Token": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_public_widget_config_exposes_only_public_fields(async_client):
    _headers, agent = await _register_and_create_agent(async_client)
    tok = {"X-Agent-Token": agent["public_token"]}

    res = await async_client.get(f"/api/public/agents/{agent['id']}/config", headers=tok)
    assert res.status_code == 200
    cfg = res.json()
    assert cfg["name"] == "Chat Bot"
    assert "public_token" not in cfg
    assert "user_id" not in cfg


# -------------------------------------------------------- service-level SSE
@pytest.mark.asyncio
async def test_chat_streams_full_event_sequence(async_client):
    """The public widget chat emits the complete SSE event contract."""
    _headers, agent = await _register_and_create_agent(async_client)
    thread_id = "preview-1"
    await _start_public_chat(async_client, agent, thread_id)

    text = await _collect_stream(f"a{agent['id']}:{thread_id}")
    assert "event: lifecycle" in text and "running" in text
    assert "event: lifecycle" in text and "completed" in text
    assert "event: message_start" in text
    assert "event: text_delta" in text
    assert "Hello " in text
    assert "world!" in text
    assert "event: tool_start" in text
    assert "search_knowledge_base" in text
    assert "event: tool_end" in text
    assert "event: message_end" in text
    # structured sources event carries the EXACT URLs from the tool output
    assert 'event: sources' in text
    assert '"https://example.com"' in text
    assert '"https://example.com/docs"' in text
    assert '"Example"' in text


@pytest.mark.asyncio
async def test_stream_terminates_after_completed_lifecycle(async_client):
    """The SSE stream must END after the terminal lifecycle event.

    Before the fix the generator looped on keep-alives forever, so the
    widget never left the streaming state ("loading tanpa henti") and the
    send button stayed disabled.
    """
    _headers, agent = await _register_and_create_agent(async_client)
    thread_id = "preview-end"
    await _start_public_chat(async_client, agent, thread_id)

    # Consumes the generator to its natural end — will hang (and time out)
    # if the stream never closes.
    text = await _collect_stream_until_end(f"a{agent['id']}:{thread_id}")
    assert "event: lifecycle" in text
    assert '"event": "completed"' in text
    assert "keepalive" not in text


@pytest.mark.asyncio
async def test_public_widget_history_returns_messages(async_client):
    _headers, agent = await _register_and_create_agent(async_client)
    thread_id = "history-1"
    await _start_public_chat(async_client, agent, thread_id)
    await _collect_stream(f"a{agent['id']}:{thread_id}")

    # The fake graph never persists messages, so history is empty — but the
    # endpoint must not error.
    res = await async_client.get(
        f"/api/public/agents/{agent['id']}/history?thread_id={thread_id}",
        headers={"X-Agent-Token": agent["public_token"]},
    )
    assert res.status_code == 200
    assert "messages" in res.json()
