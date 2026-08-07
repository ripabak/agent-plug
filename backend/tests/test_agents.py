"""API tests for agent CRUD, personalization, token rotation, embed snippet."""
import re
import uuid

AGENT = {
    "name": "Docs Bot",
    "description": "Answers questions about our docs",
    "welcome_message": "Hello!",
    "avatar_emoji": "🦊",
}


def _create_agent(client, headers, **overrides):
    payload = {**AGENT, **overrides}
    res = client.post("/api/agents", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


class TestAgentAPI:
    def test_create_agent_generates_token(self, client, auth_headers):
        headers, _ = auth_headers
        agent = _create_agent(client, headers)
        assert len(agent["public_token"]) >= 32
        assert agent["name"] == "Docs Bot"
        # fresh agents are baked with the platform theme preset
        assert agent["chat_theme"] == (
            '{"preset": "platform", "custom": {}, "touched": false}'
        )

    def test_create_requires_auth(self, client):
        assert client.post("/api/agents", json=AGENT).status_code == 401

    def test_list_and_patch(self, client, auth_headers):
        headers, _ = auth_headers
        agent = _create_agent(client, headers)
        res = client.get("/api/agents", headers=headers)
        assert [a["id"] for a in res.json()] == [agent["id"]]

        res = client.patch(
            f"/api/agents/{agent['id']}", json={"name": "Renamed"}, headers=headers
        )
        assert res.status_code == 200
        assert res.json()["name"] == "Renamed"
        # other fields unchanged (theme preset survives the patch)
        assert res.json()["chat_theme"] == agent["chat_theme"]

    def test_ownership_enforced(self, client, auth_headers):
        headers, _ = auth_headers
        agent = _create_agent(client, headers)

        # second user cannot see/update/delete the agent
        res2 = client.post(
            "/api/auth/register",
            json={"email": f"other-{uuid.uuid4().hex}@example.com", "display_name": "Other", "password": "secret123"},
        )
        other_headers = {"Authorization": f"Bearer {res2.json()['access_token']}"}

        assert client.get(f"/api/agents/{agent['id']}", headers=other_headers).status_code == 404
        assert client.patch(f"/api/agents/{agent['id']}", json={"name": "x"}, headers=other_headers).status_code == 404
        assert client.delete(f"/api/agents/{agent['id']}", headers=other_headers).status_code == 404

    def test_regenerate_token(self, client, auth_headers):
        headers, _ = auth_headers
        agent = _create_agent(client, headers)
        res = client.post(f"/api/agents/{agent['id']}/regenerate-token", headers=headers)
        assert res.status_code == 200
        assert res.json()["public_token"] != agent["public_token"]

    def test_delete_agent(self, client, auth_headers):
        headers, _ = auth_headers
        agent = _create_agent(client, headers)
        assert client.delete(f"/api/agents/{agent['id']}", headers=headers).status_code == 204
        assert client.get(f"/api/agents/{agent['id']}", headers=headers).status_code == 404

    def test_embed_snippet_contains_ids(self, client, auth_headers):
        headers, _ = auth_headers
        agent = _create_agent(client, headers)
        res = client.get(f"/api/agents/{agent['id']}/embed", headers=headers)
        assert res.status_code == 200
        body = res.json()
        html = body["html"]
        assert f'data-agent-id="{agent["id"]}"' in html
        assert f'data-token="{agent["public_token"]}"' in html
        assert re.search(r"src=\"[^\"]+widget\.js\"", html)

    def test_chat_display_config_roundtrip(self, client, auth_headers):
        """Chat theme + show thinking/tools toggles persist and reach the widget config."""
        headers, _ = auth_headers
        agent = _create_agent(
            client,
            headers,
            chat_theme='{"preset": "emerald", "custom": {"headerBg": "#123456"}, "touched": true}',
            show_thinking=False,
            show_tools=True,
        )
        # values persisted on create
        assert agent["show_thinking"] is False
        assert agent["show_tools"] is True
        assert "emerald" in agent["chat_theme"]

        # PATCH updates the display config
        res = client.patch(
            f"/api/agents/{agent['id']}",
            json={"chat_theme": '{"preset": "slate", "custom": {}, "touched": true}', "show_thinking": True},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["show_thinking"] is True
        assert "slate" in res.json()["chat_theme"]
        assert res.json()["show_tools"] is True  # untouched field kept

        # widget public config exposes the same values (token auth)
        cfg = client.get(
            f"/api/public/agents/{agent['id']}/config",
            headers={"X-Agent-Token": agent["public_token"]},
        )
        assert cfg.status_code == 200
        body = cfg.json()
        assert body["show_thinking"] is True
        assert body["show_tools"] is True
        assert "slate" in body["chat_theme"]
