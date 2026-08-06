"""Embed snippet generation for agents."""
from ..config import BACKEND_PUBLIC_URL
from ..models import Agent


def build_embed_snippet(agent: Agent) -> str:
    """Build the HTML snippet users paste into their website.

    The snippet is a plain <script> tag whose data-* attributes identify the
    agent and carry the public token used to authenticate widget requests.
    """
    base = BACKEND_PUBLIC_URL.rstrip("/")
    return (
        f'<script src="{base}/api/public/widget.js" '
        f'data-agent-id="{agent.id}" '
        f'data-token="{agent.public_token}" '
        f'data-base-url="{base}"></script>'
    )
