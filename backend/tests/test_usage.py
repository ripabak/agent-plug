"""Tests for the usage dashboard: per-run usage rows + /agents/{id}/usage API.

Uses a FAKE agent graph (no real LLM calls) injected by monkeypatching
`app.services.agent_session_service.build_agent` — same pattern as
test_chat_api.py. Each finished run must write one `agent_usage` row with
the aggregated token counts, and the usage endpoint must return totals +
daily series + paginated history.
"""
import asyncio
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
        async def _gen():
            yield {"method": "messages", "params": {"data": ({"event": "message-start"},)}}
            yield {
                "method": "messages",
                "params": {"data": ({"event": "content-block-delta", "delta": {"type": "text-delta", "text": "Hi"}},)},
            }
            yield {
                "method": "messages",
                "params": {"data": (
                    {
                        "event": "message-finish",
                        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                        "metadata": {"model_name": "test-model"},
                    },
                )},
            }

        return _gen()


@pytest.fixture(autouse=True)
def _fake_agent(monkeypatch):
    async def fake_build_agent(db, agent_id, checkpointer):
        return FakeAgent(agent_id)

    monkeypatch.setattr("app.services.agent_session_service.build_agent", fake_build_agent)


@pytest.fixture()
async def async_client():
    await init_checkpointer()
    transport = httpx.ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    # Let background runs finish (they may spawn usage log tasks), then
    # drain the fire-and-forget usage writes before the loop closes.
    await svc.drain_run_tasks()
    await drain_usage_logs()
    await close_checkpointer()


async def _register_and_create_agent(async_client) -> tuple[dict, dict, int]:
    email = f"usage-{uuid.uuid4().hex}@example.com"
    res = await async_client.post(
        "/api/auth/register",
        json={"email": email, "display_name": "Usage", "password": "secret123"},
    )
    assert res.status_code == 201
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    user_id = res.json()["user"]["id"]
    res = await async_client.post("/api/agents", json={"name": "Usage Bot"}, headers=headers)
    assert res.status_code == 201
    return headers, res.json(), user_id


async def _run_preview_chat(
    async_client, headers, agent_id: int, thread: str, user_id: int, page_url: str | None = None
) -> None:
    res = await async_client.post(
        f"/api/threads/{thread}/commands",
        json={
            "method": "run.start",
            "id": "c1",
            "params": {
                "input": {
                    "agent_id": agent_id,
                    "messages": [{"role": "user", "content": "hi"}],
                    **({"page_url": page_url} if page_url else {}),
                }
            },
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["type"] == "success"
    await _collect_stream(f"u{user_id}:{thread}")


async def _run_widget_chat(async_client, agent: dict, thread: str, page_url: str | None = None) -> None:
    tok = {"X-Agent-Token": agent["public_token"]}
    res = await async_client.post(
        f"/api/public/agents/{agent['id']}/commands",
        json={
            "method": "run.start",
            "id": "c1",
            "params": {
                "input": {
                    "thread_id": thread,
                    "messages": [{"role": "user", "content": "hi widget"}],
                    **({"page_url": page_url} if page_url else {}),
                }
            },
        },
        headers=tok,
    )
    assert res.status_code == 200
    assert res.json()["type"] == "success"
    await _collect_stream(f"a{agent['id']}:{thread}")


async def _collect_stream(thread_key: str) -> str:
    frames = []
    async for frame in svc.stream_events(thread_key, ["*"], 0):
        frames.append(frame)
        if "event: lifecycle" in frame and "completed" in frame:
            break
    return "\n".join(frames)


async def _wait_for_usage(async_client, headers, agent_id: int, expected_total: int, timeout=3.0):
    """Poll the usage endpoint until the expected row count appears.

    The run task commits the usage row right after the terminal lifecycle
    event is buffered, so the SSE stream may end a moment before the row is
    visible — retry briefly to avoid flaky timing.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        res = await async_client.get(f"/api/agents/{agent_id}/usage?page_size=50", headers=headers)
        assert res.status_code == 200
        body = res.json()
        if body["total"] >= expected_total:
            return body
        await asyncio.sleep(0.05)
    raise AssertionError(f"usage rows never reached {expected_total}")


@pytest.mark.asyncio
async def test_usage_rows_carry_page_url(async_client):
    """The usage row records WHERE the widget was embedded (page_url)."""
    headers, agent, user_id = await _register_and_create_agent(async_client)
    await _run_preview_chat(
        async_client,
        headers,
        agent["id"],
        "page-url-thread",
        user_id,
        page_url="https://shop.example.com/items/42",
    )
    await _run_widget_chat(
        async_client, agent, "page-url-widget", page_url="https://landing.example.com/pricing"
    )

    body = await _wait_for_usage(async_client, headers, agent["id"], expected_total=2)
    urls = {i["page_url"] for i in body["items"]}
    assert urls == {"https://shop.example.com/items/42", "https://landing.example.com/pricing"}


# ------------------------------------------------------------------- tests
@pytest.mark.asyncio
async def test_runs_write_usage_rows_and_summary(async_client):
    headers, agent, user_id = await _register_and_create_agent(async_client)

    # two preview chats + one widget chat = 3 requests
    await _run_preview_chat(async_client, headers, agent["id"], "u-thread-1", user_id)
    await _run_preview_chat(async_client, headers, agent["id"], "u-thread-2", user_id)
    await _run_widget_chat(async_client, agent, "w-thread-1")

    body = await _wait_for_usage(async_client, headers, agent["id"], expected_total=3)
    summary = body["summary"]
    assert summary["total_requests"] == 3
    assert summary["total_input_tokens"] == 300  # 3 × 100
    assert summary["total_output_tokens"] == 150  # 3 × 50
    assert summary["total_tokens"] == 450

    # daily series: today is the last bucket and holds all 3 requests
    assert summary["series"][-1]["requests"] == 3
    assert summary["series"][-1]["input_tokens"] == 300
    assert len(summary["series"]) == 30  # default days window

    # history: newest first, both channels present, token fields populated
    items = body["items"]
    assert len(items) == 3
    channels = {i["channel"] for i in items}
    assert channels == {"preview", "widget"}
    assert all(i["input_tokens"] == 100 and i["output_tokens"] == 50 for i in items)
    assert all(i["model"] == "test-model" and i["status"] == "completed" for i in items)


@pytest.mark.asyncio
async def test_usage_history_pagination(async_client):
    headers, agent, user_id = await _register_and_create_agent(async_client)

    for n in range(3):
        await _run_preview_chat(async_client, headers, agent["id"], f"page-thread-{n}", user_id)

    await _wait_for_usage(async_client, headers, agent["id"], expected_total=3)
    res = await async_client.get(
        f"/api/agents/{agent['id']}/usage?page=1&page_size=2", headers=headers
    )
    assert res.status_code == 200
    page1 = res.json()
    assert page1["total"] == 3
    assert page1["pages"] == 2
    assert len(page1["items"]) == 2
    assert page1["page"] == 1

    res = await async_client.get(
        f"/api/agents/{agent['id']}/usage?page=2&page_size=2", headers=headers
    )
    page2 = res.json()
    assert len(page2["items"]) == 1
    # newest first: page 2 holds the oldest row
    assert page1["items"][0]["created_at"] >= page2["items"][0]["created_at"]


@pytest.mark.asyncio
async def test_usage_requires_owned_agent(async_client):
    headers, agent, _ = await _register_and_create_agent(async_client)
    res = await async_client.post(
        "/api/auth/register",
        json={"email": f"other-{uuid.uuid4().hex}@example.com", "display_name": "O", "password": "secret123"},
    )
    other = {"Authorization": f"Bearer {res.json()['access_token']}"}

    res = await async_client.get(f"/api/agents/{agent['id']}/usage", headers=other)
    assert res.status_code == 404
    # unauthenticated
    assert (await async_client.get(f"/api/agents/{agent['id']}/usage")).status_code == 401


@pytest.mark.asyncio
async def test_usage_records_client_country(async_client, monkeypatch):
    """Client IP (via X-Forwarded-For) is geolocated and stored on the row."""
    def fake_resolve(_ip):
        return "ID"

    monkeypatch.setattr("app.services.usage_service.resolve_country", fake_resolve)
    headers, agent, user_id = await _register_and_create_agent(async_client)

    res = await async_client.post(
        "/api/threads/country-1/commands",
        json={
            "method": "run.start",
            "id": "c1",
            "params": {"input": {"agent_id": agent["id"], "messages": [{"role": "user", "content": "hi"}]}},
        },
        headers={**headers, "X-Forwarded-For": "8.8.8.8"},
    )
    assert res.status_code == 200
    await _collect_stream(f"u{user_id}:country-1")

    body = await _wait_for_usage(async_client, headers, agent["id"], expected_total=1)
    assert body["items"][0]["country"] == "ID"
    # country breakdown in the summary
    assert body["summary"]["countries"] == [{"country": "ID", "requests": 1}]


@pytest.mark.asyncio
async def test_usage_empty_agent_returns_zeroed_series(async_client):
    headers, agent, _ = await _register_and_create_agent(async_client)
    res = await async_client.get(f"/api/agents/{agent['id']}/usage", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["total_requests"] == 0
    assert body["total"] == 0
    assert len(body["summary"]["series"]) == 30
    assert all(p["requests"] == 0 for p in body["summary"]["series"])
    assert body["items"] == []
