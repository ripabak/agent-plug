"""Tests for the read_current_page tool (current-page context) + page_url transport.

The tool is exercised directly with a monkeypatched fetcher; the transport
(page_url from run.start → AgentThread.page_url) is tested through the public
widget command endpoint with a fake agent graph (no real LLM calls).
"""
import uuid

import httpx
import pytest
from sqlalchemy import select

from app.agent.checkpointer import close_checkpointer, init_checkpointer
from app.agent.tools import create_fetch_web_tool, create_page_tool
from app.database import async_session
from app.models import Agent, AgentThread, User
from app.rag.fetcher import Page


async def _seed_thread(page_url: str | None) -> str:
    async with async_session() as db:
        user = User(
            email=f"page-{uuid.uuid4().hex}@example.com",
            display_name="Page",
            hashed_password="x",
        )
        db.add(user)
        await db.flush()
        agent = Agent(user_id=user.id, name="Page Bot", public_token=f"tok_{uuid.uuid4().hex}")
        db.add(agent)
        await db.flush()
        thread_key = f"a{agent.id}:t-{uuid.uuid4().hex}"
        db.add(AgentThread(thread_id=thread_key, agent_id=agent.id, page_url=page_url))
        await db.commit()
        return thread_key


def _fake_page(url: str) -> Page:
    return Page(url=url, title="Current Page", text="This page explains pricing. " * 40)


@pytest.mark.asyncio
async def test_read_current_page_returns_content(monkeypatch):
    thread_key = await _seed_thread("https://example.com/current")
    monkeypatch.setattr("app.agent.tools.fetch_page", lambda url, client=None: _fake_page(url))

    result = await create_page_tool(1).ainvoke({}, {"configurable": {"thread_id": thread_key}})

    assert "Current Page" in result
    assert "This page explains pricing" in result
    # the source marker makes the widget render a source chip for the page
    assert "[Source: https://example.com/current" in result


@pytest.mark.asyncio
async def test_read_current_page_truncates_long_text(monkeypatch):
    thread_key = await _seed_thread("https://example.com/long")
    long_text = "word " * 5000  # 25k chars — well over PAGE_CONTEXT_MAX_CHARS (10k)
    monkeypatch.setattr(
        "app.agent.tools.fetch_page",
        lambda url, client=None: Page(url=url, title="Long Page", text=long_text),
    )

    result = await create_page_tool(1).ainvoke({}, {"configurable": {"thread_id": thread_key}})

    assert len(result) < 11000
    assert "…" in result


@pytest.mark.asyncio
async def test_read_current_page_blocks_private_urls(monkeypatch):
    """SSRF guard: the backend must never fetch internal addresses."""
    def should_not_fetch(url, client=None):  # pragma: no cover
        raise AssertionError("fetch must not run for blocked URLs")

    monkeypatch.setattr("app.agent.tools.fetch_page", should_not_fetch)
    tool = create_page_tool(1)

    for blocked in (
        "http://localhost:8000/admin",
        "http://169.254.169.254/latest/meta-data",  # cloud metadata
        "http://10.0.0.1/internal",
        "https://127.0.0.1/",
    ):
        thread_key = await _seed_thread(blocked)
        result = await tool.ainvoke({}, {"configurable": {"thread_id": thread_key}})
        assert "Could not read the current page" in result, blocked


@pytest.mark.asyncio
async def test_read_current_page_without_url():
    thread_key = await _seed_thread(None)
    result = await create_page_tool(1).ainvoke({}, {"configurable": {"thread_id": thread_key}})
    assert "No current page context" in result


# ------------------------------------------------------- fetch_web_page (by URL)


@pytest.mark.asyncio
async def test_fetch_web_page_by_url(monkeypatch):
    monkeypatch.setattr("app.agent.tools.fetch_page", lambda url, client=None: _fake_page(url))

    result = await create_fetch_web_tool().ainvoke({"url": "https://example.com/page"})

    assert "Current Page" in result
    assert "[Source: https://example.com/page" in result


@pytest.mark.asyncio
async def test_fetch_web_page_normalizes_bare_host(monkeypatch):
    monkeypatch.setattr("app.agent.tools.fetch_page", lambda url, client=None: _fake_page(url))

    result = await create_fetch_web_tool().ainvoke({"url": "example.com"})

    # model passed a bare host — the tool assumes https://
    assert "[Source: https://example.com" in result


@pytest.mark.asyncio
async def test_fetch_web_page_blocks_private_urls(monkeypatch):
    def should_not_fetch(url, client=None):  # pragma: no cover
        raise AssertionError("fetch must not run for blocked URLs")

    monkeypatch.setattr("app.agent.tools.fetch_page", should_not_fetch)

    for blocked in ("http://localhost:8000/", "http://10.0.0.1/internal", "https://169.254.169.254/x"):
        result = await create_fetch_web_tool().ainvoke({"url": blocked})
        assert "Could not fetch" in result, blocked


@pytest.mark.asyncio
async def test_fetch_web_page_rejects_invalid_url(monkeypatch):
    def should_not_fetch(url, client=None):  # pragma: no cover
        raise AssertionError("fetch must not run for invalid URLs")

    monkeypatch.setattr("app.agent.tools.fetch_page", should_not_fetch)

    for bad in ("ftp://example.com/file", "javascript:alert(1)", "   "):
        result = await create_fetch_web_tool().ainvoke({"url": bad})
        assert "Could not fetch" in result, bad


# ---------------------------------------------------------------- transport


@pytest.fixture()
async def async_client():
    """Async client with ASGITransport; inits the checkpointer on the same loop."""
    await init_checkpointer()
    app = __import__("app.main", fromlist=["app"]).app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    from app.services import agent_session_service as svc
    from app.services.usage_service import drain_usage_logs

    await svc.drain_run_tasks()
    await drain_usage_logs()
    await close_checkpointer()


class _FakeState:
    def __init__(self):
        self.values = {"messages": []}


class _FakeAgent:
    """Mimics the compiled graph surface used by start_agent_run."""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.state = _FakeState()

    async def aget_state(self, config):
        return self.state

    async def astream_events(self, input, config, version="v3"):
        async def _gen():
            yield {"method": "messages", "params": {"data": ({"event": "message-start"},)}}
            yield {
                "method": "messages",
                "params": {
                    "data": ({"event": "message-finish", "usage": {"total_tokens": 1}, "metadata": {}},)
                },
            }

        return _gen()


@pytest.mark.asyncio
async def test_run_start_persists_page_url(async_client, monkeypatch):
    """The widget's run.start `page_url` lands on the thread row."""
    from app.services import agent_session_service as svc

    async def fake_build_agent(db, agent_id, checkpointer):
        return _FakeAgent(agent_id)

    monkeypatch.setattr("app.services.agent_session_service.build_agent", fake_build_agent)

    res = await async_client.post(
        "/api/auth/register",
        json={"email": f"page-{uuid.uuid4().hex}@example.com", "display_name": "Page", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    res = await async_client.post(
        "/api/agents", json={"name": "Page Bot", "description": "d"}, headers=headers
    )
    agent = res.json()

    res = await async_client.post(
        f"/api/public/agents/{agent['id']}/commands",
        headers={"X-Agent-Token": agent["public_token"]},
        json={
            "method": "run.start",
            "id": "c1",
            "params": {
                "input": {
                    "thread_id": "t1",
                    "messages": [{"role": "user", "content": "what's on this page?"}],
                    "page_url": "https://example.com/current",
                }
            },
        },
    )
    assert res.status_code == 200
    assert res.json()["type"] == "success"

    # wait for the background run to finish (it upserts the thread mapping)
    thread_key = f"a{agent['id']}:t1"
    async for _ in svc.stream_events(thread_key, ["*"], 0):
        pass

    async with async_session() as db:
        mapping = (
            await db.execute(select(AgentThread).where(AgentThread.thread_id == thread_key))
        ).scalar_one()
    assert mapping.page_url == "https://example.com/current"
