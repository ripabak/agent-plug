"""Tests for embed snippet generation and the widget contract."""
from app.models import Agent
from app.services.embed import build_embed_snippet


def _agent() -> Agent:
    a = Agent(id=7, name="Test", public_token="tok_abc123")
    return a


def test_build_embed_snippet():
    html = build_embed_snippet(_agent())
    assert 'src="http://localhost:8000/api/public/widget.js"' in html
    assert 'data-agent-id="7"' in html
    assert 'data-token="tok_abc123"' in html
    assert 'data-base-url="http://localhost:8000"' in html


def test_widget_js_is_served(client):
    res = client.get("/api/public/widget.js")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/javascript")
    body = res.text
    # must be dependency-free IIFE with the required markers
    assert "(function () {" in body
    assert "data-agent-id" in body
    assert "run.start" in body
    assert "/stream" in body
    assert "addEventListener" in body  # CSP-friendly, no inline handlers
    # assistant messages render markdown (escape-first: raw HTML never lands)
    assert "markdownToHtml" in body
    assert "mdInline" in body
    assert "<strong>" in body
