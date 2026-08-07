"""Unit tests for system prompt composition (`build_system_prompt`).

Verifies the persona prompt is ADDITIVE: the base prompt (knowledge base +
citation rules) stays intact and the persona is appended, never replacing it.
"""
from app.agent.agent import build_system_prompt
from app.models import Agent


def _agent(**overrides) -> Agent:
    defaults = {
        "id": 1,
        "user_id": 1,
        "name": "Docs Bot",
        "description": "Answers questions about our docs",
        "persona_prompt": None,
        "welcome_message": "Hello!",
        "avatar_emoji": "🤖",
        "avatar_path": None,
        "avatar_kind": "photo",
        "chat_theme": "",
        "show_thinking": False,
        "show_tools": True,
        "public_token": "tok",
    }
    return Agent(**{**defaults, **overrides})


def test_base_prompt_uses_name_and_description():
    prompt = build_system_prompt(_agent())
    assert "You are Docs Bot" in prompt
    assert "Answers questions about our docs" in prompt
    # Core rules always present.
    assert "search_knowledge_base" in prompt
    assert "Knowledge Base" in prompt


def test_no_persona_by_default():
    prompt = build_system_prompt(_agent())
    assert "\n\n## Persona" not in prompt


def test_persona_appended_not_replacing():
    prompt = build_system_prompt(_agent(persona_prompt="Be very casual and use emojis."))
    assert prompt.startswith("You are Docs Bot")
    assert "\n\n## Persona\nBe very casual and use emojis." in prompt
    # Base rules come before the persona section.
    assert prompt.index("Knowledge Base") < prompt.index("## Persona")


def test_blank_persona_ignored():
    assert "\n\n## Persona" not in build_system_prompt(_agent(persona_prompt="   "))


def test_persona_round_trips_through_api(client, auth_headers):
    """Create + patch an agent with a persona prompt and read it back."""
    headers, _ = auth_headers
    res = client.post(
        "/api/agents",
        json={"name": "Persona Bot", "persona_prompt": "Be super friendly!"},
        headers=headers,
    )
    assert res.status_code == 201
    agent = res.json()
    assert agent["persona_prompt"] == "Be super friendly!"

    res = client.patch(
        f"/api/agents/{agent['id']}", json={"persona_prompt": None}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["persona_prompt"] is None
