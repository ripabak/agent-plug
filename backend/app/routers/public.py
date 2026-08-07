"""Public (widget) routes: token-authenticated chat + agent config + widget.js.

These endpoints are used by the embeddable widget on external websites.
Authentication = `X-Agent-Token` header containing the agent's public_token
(the same token embedded in the user's HTML snippet).
"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Agent
from ..schemas import AgentPublicConfig, CommandResponse, RunStartInput
from ..storage import storage
from ..services.agent_session_service import (
    get_thread_history,
    start_agent_run,
    stop_agent_run,
    stream_events,
)
from ..services.geo import request_client_ip

router = APIRouter(prefix="/api/public", tags=["public-widget"])

_WIDGET_JS_PATH = Path(__file__).resolve().parents[1] / "widget" / "widget.js"


async def _get_agent_by_token(agent_id: int, token: str | None, db: AsyncSession) -> Agent:
    """Resolve an agent by id + public token (401 on missing/mismatch)."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing agent token")
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None or agent.public_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token")
    return agent


def _error(cmd_id, code: str, message: str) -> CommandResponse:
    return CommandResponse(type="error", id=cmd_id, error=code, message=message)


@router.get("/agents/{agent_id}/avatar")
async def get_avatar(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Serve the agent's avatar image (public — needed by <img> in the widget).

    No token: an avatar is a non-sensitive logo, and image tags cannot send
    the X-Agent-Token header. Falls back to 404 when no photo is uploaded.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None or not agent.avatar_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    data = await storage.get(agent.avatar_path)
    return Response(
        content=data,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/agents/{agent_id}/config", response_model=AgentPublicConfig)
async def get_agent_config(
    agent_id: int,
    response: Response,
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Public bootstrap data for the widget (non-secret fields only).

    `Cache-Control: no-cache` so the widget always revalidates — config
    changes (theme, avatar URL) must not be served from a stale cache.
    """
    response.headers["Cache-Control"] = "no-cache"
    agent = await _get_agent_by_token(agent_id, x_agent_token, db)
    return AgentPublicConfig.model_validate(agent)


@router.post("/agents/{agent_id}/commands", response_model=CommandResponse)
async def handle_command(
    agent_id: int,
    request: Request,
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Widget command endpoint: run.start / run.cancel (token-authenticated)."""
    agent = await _get_agent_by_token(agent_id, x_agent_token, db)
    try:
        command = await request.json()
    except json.JSONDecodeError:
        return _error(None, "invalid_request", "Invalid JSON body")

    method = command.get("method", "")
    cmd_id = command.get("id")

    if method == "run.start":
        input_data = RunStartInput.model_validate(command.get("params", {}).get("input") or {})
        thread_id = input_data.thread_id or ""
        if not thread_id:
            return _error(cmd_id, "invalid_input", "thread_id is required in input")
        thread_key = f"a{agent.id}:{thread_id}"
        run_id = await start_agent_run(
            thread_key=thread_key,
            agent_id=agent.id,
            messages=[m.model_dump() for m in input_data.messages],
            user_id=None,
            client_ip=request_client_ip(request),
        )
        return CommandResponse(type="success", id=cmd_id, result={"run_id": run_id})

    if method == "run.cancel":
        thread_id = (command.get("params", {}) or {}).get("thread_id", "")
        if thread_id:
            stop_agent_run(f"a{agent.id}:{thread_id}")
        return CommandResponse(type="success", id=cmd_id, result={"cancelled": True})

    return _error(cmd_id, "unknown_command", f"Unsupported command: {method}")


@router.post("/agents/{agent_id}/stream")
async def handle_stream(
    agent_id: int,
    request: Request,
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Widget SSE stream (token-authenticated)."""
    agent = await _get_agent_by_token(agent_id, x_agent_token, db)
    params = await request.json()
    thread_id = params.get("thread_id", "")
    if not thread_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="thread_id is required")

    channels_str = params.get("channels", "values,lifecycle")
    if isinstance(channels_str, list):
        channel_list = channels_str
    else:
        channel_list = [c.strip() for c in channels_str.split(",") if c.strip()]
    since = params.get("since", 0)

    return StreamingResponse(
        stream_events(f"a{agent.id}:{thread_id}", channel_list, since),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/agents/{agent_id}/history")
async def get_history(
    agent_id: int,
    thread_id: str,
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Return message history for a public widget thread."""
    agent = await _get_agent_by_token(agent_id, x_agent_token, db)
    messages = await get_thread_history(f"a{agent.id}:{thread_id}")
    return {"messages": messages}


@router.get("/widget.js")
async def widget_js():
    """Serve the self-contained widget script (no build step, no dependencies)."""
    return Response(
        content=_WIDGET_JS_PATH.read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )
