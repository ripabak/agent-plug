"""Tests for the read-only admin API (env-configured admin principal).

The admin is NOT a User row: login uses ADMIN_EMAIL/ADMIN_PASSWORD from env
(monkeypatched per-test via `app.config` module attrs), and every data
endpoint is GET-only.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app import config
from app.database import async_session
from app.main import app
from app.models import AgentUsage, Source

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-secret-123"


@pytest.fixture()
def admin_env(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setattr(config, "ADMIN_PASSWORD", ADMIN_PASSWORD)


@pytest.fixture()
def client():
    return TestClient(app)


def _admin_headers(client: TestClient) -> dict:
    res = client.post(
        "/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _register_user(client: TestClient, name: str) -> dict:
    email = f"{name}-{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "display_name": name.title(), "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_agent(client: TestClient, token: str, name: str) -> dict:
    res = client.post(
        "/api/agents", json={"name": name}, headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _add_usage(agent_id: int, input_tokens: int, output_tokens: int) -> None:
    """Insert one usage row directly (usage rows are written by the chat runtime)."""
    db = async_session()
    try:
        db.add(
            AgentUsage(
                agent_id=agent_id,
                thread_id="seed",
                model="test-model",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost=None,
                status="completed",
            )
        )
        await db.commit()
    finally:
        await db.close()


async def _add_source(agent_id: int, kind: str = "url", status: str = "ready") -> None:
    db = async_session()
    try:
        db.add(
            Source(
                agent_id=agent_id,
                url=f"https://example.com/{uuid.uuid4().hex}",
                kind=kind,
                status=status,
                chunk_count=3 if status == "ready" else 0,
            )
        )
        await db.commit()
    finally:
        await db.close()


# ------------------------------------------------------------------- auth


def test_admin_disabled_when_not_configured(client, monkeypatch):
    """No ADMIN_EMAIL/ADMIN_PASSWORD -> every admin endpoint returns 403.

    Hermetic: explicitly clears config (the dev .env may set credentials).
    """
    monkeypatch.setattr(config, "ADMIN_EMAIL", "")
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "")
    res = client.post(
        "/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 403
    res = client.get("/api/admin/users")
    assert res.status_code == 403


def test_admin_login_rejects_wrong_credentials(admin_env, client):
    res = client.post(
        "/api/admin/login", json={"email": ADMIN_EMAIL, "password": "wrong-password"}
    )
    assert res.status_code == 401
    res = client.post(
        "/api/admin/login", json={"email": "other@example.com", "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 401


def test_admin_login_and_me(admin_env, client):
    res = client.post(
        "/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["access_token"]

    res = client.get(
        "/api/admin/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert res.status_code == 200
    assert res.json()["email"] == ADMIN_EMAIL


def test_regular_user_token_cannot_access_admin(admin_env, client):
    user = _register_user(client, "sneaky")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    for path in ("/api/admin/users", "/api/admin/stats"):
        res = client.get(path, headers=headers)
        assert res.status_code == 403, path


# --------------------------------------------------------------- monitoring


@pytest.mark.asyncio
async def test_admin_stats_totals(admin_env, client):
    """Stats are platform-wide; assert as a DELTA against a baseline so tests
    never depend on each other's leftovers."""
    base = client.get("/api/admin/stats", headers=_admin_headers(client))
    assert base.status_code == 200
    base_body = base.json()

    u1 = _register_user(client, "statsa")
    u2 = _register_user(client, "statsb")
    a1 = _create_agent(client, u1["access_token"], "Stats Bot A")
    a2 = _create_agent(client, u2["access_token"], "Stats Bot B")
    await _add_usage(a1["id"], 100, 50)
    await _add_usage(a1["id"], 10, 20)
    await _add_usage(a2["id"], 300, 0)

    body = client.get("/api/admin/stats", headers=_admin_headers(client)).json()
    assert body["total_users"] - base_body["total_users"] == 2
    assert body["total_agents"] - base_body["total_agents"] == 2
    assert body["total_requests"] - base_body["total_requests"] == 3
    assert body["total_tokens"] - base_body["total_tokens"] == 480  # 150+30+300
    assert body["total_input_tokens"] - base_body["total_input_tokens"] == 410
    assert body["total_output_tokens"] - base_body["total_output_tokens"] == 70

    # today's bucket (the last series point) gained exactly our 3 requests
    assert body["series"][-1]["requests"] - base_body["series"][-1]["requests"] == 3
    assert len(body["series"]) == 30  # default days window


@pytest.mark.asyncio
async def test_admin_users_pagination_and_search(admin_env, client):
    names = ["alpha", "beta", "gamma"]
    for n in names:
        _register_user(client, n)
    # create one agent + usage for alpha so aggregates are exercised
    u = _register_user(client, "pagi-user")
    agent = _create_agent(client, u["access_token"], "Pagi Bot")
    await _add_usage(agent["id"], 5, 5)

    headers = _admin_headers(client)
    body = client.get("/api/admin/users", headers=headers).json()
    assert body["total"] >= 4
    assert body["pages"] >= 1
    assert body["page"] == 1
    # the pagi-user row carries aggregates
    row = next(r for r in body["items"] if r["email"] == u["user"]["email"])
    assert row["agent_count"] == 1
    assert row["total_requests"] == 1
    assert row["total_tokens"] == 10
    assert row["last_active"] is not None

    # search narrows by email
    found = client.get(
        "/api/admin/users", params={"q": "pagi-user"}, headers=headers
    ).json()
    assert found["total"] == 1
    assert found["items"][0]["email"] == u["user"]["email"]

    # search by display name works too ("pagi-user".title() -> "Pagi-User")
    found = client.get(
        "/api/admin/users", params={"q": "Pagi-User"}, headers=headers
    ).json()
    assert found["total"] == 1

    # pagination: 2 items per page over the alpha/beta/gamma set
    found = client.get(
        "/api/admin/users", params={"q": "alpha"}, headers=headers
    ).json()
    assert found["total"] == 1

    # page_size=2 splits a filtered set of 3
    trio = client.get(
        "/api/admin/users",
        params={"q": "example.com", "page_size": 2, "page": 1},
        headers=headers,
    ).json()
    assert trio["page_size"] == 2
    assert trio["pages"] == (trio["total"] + 1) // 2
    assert len(trio["items"]) == 2
    page2 = client.get(
        "/api/admin/users",
        params={"q": "example.com", "page_size": 2, "page": 2},
        headers=headers,
    ).json()
    ids1 = {i["id"] for i in trio["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_admin_user_detail_read_only(admin_env, client):
    u = _register_user(client, "detail")
    agent = _create_agent(client, u["access_token"], "Detail Bot")
    await _add_usage(agent["id"], 40, 10)
    await _add_source(agent["id"], status="ready")
    await _add_source(agent["id"], status="failed")

    res = client.get(
        f"/api/admin/users/{u['user']['id']}", headers=_admin_headers(client)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["email"] == u["user"]["email"]
    assert body["user"]["agent_count"] == 1
    assert body["user"]["total_requests"] == 1
    assert body["user"]["total_tokens"] == 50

    (agent_row,) = body["agents"]
    assert agent_row["name"] == "Detail Bot"
    # chat_theme rides along so the admin card matches the dashboard color;
    # fresh agents are baked with the platform preset
    assert agent_row["chat_theme"] == (
        '{"preset": "platform", "custom": {}, "touched": false}'
    )
    assert agent_row["source_count"] == 2
    assert agent_row["ready_sources"] == 1
    assert agent_row["total_requests"] == 1
    assert agent_row["total_tokens"] == 50
    assert agent_row["last_active"] is not None

    # missing user -> 404
    res = client.get("/api/admin/users/999999", headers=_admin_headers(client))
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_admin_user_usage_across_agents(admin_env, client):
    u = _register_user(client, "usage")
    a1 = _create_agent(client, u["access_token"], "Usage Bot 1")
    a2 = _create_agent(client, u["access_token"], "Usage Bot 2")
    await _add_usage(a1["id"], 100, 50)
    await _add_usage(a1["id"], 10, 10)
    await _add_usage(a2["id"], 200, 0)

    res = client.get(
        f"/api/admin/users/{u['user']['id']}/usage?page_size=2",
        headers=_admin_headers(client),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    # each row is tagged with its agent so the admin table can show it
    names = {i["agent_name"] for i in body["items"]}
    assert "Usage Bot 1" in names
    assert all(i["agent_id"] in (a1["id"], a2["id"]) for i in body["items"])
    # summary aggregates across both agents
    assert body["summary"]["total_requests"] == 3
    assert body["summary"]["total_tokens"] == 370  # 150+20+200


# --------------------------------------------------------- agent drill-down


@pytest.mark.asyncio
async def test_admin_agent_detail_and_sources(admin_env, client):
    u = _register_user(client, "agentdrill")
    agent = _create_agent(client, u["access_token"], "Drill Bot")
    await _add_source(agent["id"], kind="pdf", status="ready")
    await _add_source(agent["id"], kind="url", status="failed")

    res = client.get(f"/api/admin/agents/{agent['id']}", headers=_admin_headers(client))
    assert res.status_code == 200
    body = res.json()
    assert body["agent"]["name"] == "Drill Bot"
    assert body["agent"]["public_token"]  # admin needs it for the widget preview
    assert body["user"]["email"] == u["user"]["email"]

    res = client.get(
        f"/api/admin/agents/{agent['id']}/sources", headers=_admin_headers(client)
    )
    assert res.status_code == 200
    sources = res.json()
    assert len(sources) == 2
    kinds = {s["kind"] for s in sources}
    assert kinds == {"pdf", "url"}
    statuses = {s["status"] for s in sources}
    assert statuses == {"ready", "failed"}

    # missing agent -> 404 for both
    assert client.get("/api/admin/agents/999999", headers=_admin_headers(client)).status_code == 404
    assert (
        client.get(
            "/api/admin/agents/999999/sources", headers=_admin_headers(client)
        ).status_code
        == 404
    )


@pytest.mark.asyncio
async def test_admin_agent_usage_and_embed(admin_env, client):
    u = _register_user(client, "agentusage")
    agent = _create_agent(client, u["access_token"], "Usage Drill")
    await _add_usage(agent["id"], 100, 50)
    await _add_usage(agent["id"], 10, 10)

    res = client.get(
        f"/api/admin/agents/{agent['id']}/usage?page_size=1",
        headers=_admin_headers(client),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["total_requests"] == 2
    assert body["summary"]["total_tokens"] == 170  # 150+20
    assert body["total"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 1

    res = client.get(
        f"/api/admin/agents/{agent['id']}/embed", headers=_admin_headers(client)
    )
    assert res.status_code == 200
    embed = res.json()
    assert embed["agent_id"] == agent["id"]
    assert agent["public_token"] in embed["html"]
    assert "widget.js" in embed["html"]


@pytest.mark.asyncio
async def test_admin_cannot_mutate_agents(admin_env, client):
    """Admin token must NOT work on user-scoped agent endpoints (no impersonation)."""
    u = _register_user(client, "guard")
    agent = _create_agent(client, u["access_token"], "Guard Bot")
    headers = _admin_headers(client)
    # Admin token has sub="admin" -> regular user endpoints reject it with
    # 401 (invalid token); ownership checks would 404. Either way: no access.
    res = client.patch(
        f"/api/agents/{agent['id']}", json={"name": "Hacked"}, headers=headers
    )
    assert res.status_code in (401, 403, 404)
    res = client.get(f"/api/agents/{agent['id']}", headers=headers)
    assert res.status_code in (401, 403, 404)
