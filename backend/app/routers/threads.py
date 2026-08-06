"""Authenticated chat routes (dashboard preview) — SSE agent protocol."""
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import async_session, get_db
from ..models import Agent, User
from ..schemas import CommandResponse, RunStartInput
from ..services.agent_session_service import (
    delete_thread_state,
    get_thread_history,
    session_manager,
    start_agent_run,
    stop_agent_run,
    stream_events,
)
from ..services.geo import request_client_ip

router = APIRouter(prefix="/api/threads", tags=["chat"])


def _thread_key(user_id: int, thread_id: str) -> str:
    """Namespace authed threads per user so ids can't collide/leak."""
    return f"u{user_id}:{thread_id}"


def _error(cmd_id, code: str, message: str) -> CommandResponse:
    return CommandResponse(type="error", id=cmd_id, error=code, message=message)


@router.post("/{thread_id}/commands", response_model=CommandResponse)
async def handle_command(
    thread_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run commands: `run.start` (input.agent_id + input.messages) / `run.cancel`."""
    try:
        command = await request.json()
    except json.JSONDecodeError:
        return _error(None, "invalid_request", "Invalid JSON body")

    method = command.get("method", "")
    cmd_id = command.get("id")

    if method == "run.start":
        input_data = RunStartInput.model_validate(command.get("params", {}).get("input") or {})
        if input_data.agent_id is None:
            return _error(cmd_id, "invalid_input", "agent_id is required in input")

        result = await db.execute(
            select(Agent.id).where(Agent.id == input_data.agent_id, Agent.user_id == user.id)
        )
        if not result.scalar_one_or_none():
            return _error(cmd_id, "not_found", "Agent not found or access denied")

        run_id = await start_agent_run(
            thread_key=_thread_key(user.id, thread_id),
            agent_id=input_data.agent_id,
            messages=[m.model_dump() for m in input_data.messages],
            user_id=user.id,
            client_ip=request_client_ip(request),
        )
        return CommandResponse(type="success", id=cmd_id, result={"run_id": run_id})

    if method == "run.cancel":
        stop_agent_run(_thread_key(user.id, thread_id))
        return CommandResponse(type="success", id=cmd_id, result={"cancelled": True})

    return _error(cmd_id, "unknown_command", f"Unsupported command: {method}")


@router.post("/{thread_id}/stream")
async def handle_stream(
    thread_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """SSE stream of agent events for this thread."""
    params = await request.json()
    channels_str = params.get("channels", "values,lifecycle")
    if isinstance(channels_str, list):
        channel_list = channels_str
    else:
        channel_list = [c.strip() for c in channels_str.split(",") if c.strip()]
    since = params.get("since", 0)

    return StreamingResponse(
        stream_events(_thread_key(user.id, thread_id), channel_list, since),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/{thread_id}")
async def get_history(thread_id: str, user: User = Depends(get_current_user)):
    """Return serialized message history for a thread."""
    messages = await get_thread_history(_thread_key(user.id, thread_id))
    return {"messages": messages}


@router.delete("/{thread_id}")
async def delete_thread(thread_id: str, user: User = Depends(get_current_user)):
    """Delete thread state + mapping."""
    thread_key = _thread_key(user.id, thread_id)
    async with async_session() as db:
        from ..models import AgentThread

        mapping = (
            await db.execute(
                select(AgentThread).where(
                    AgentThread.thread_id == thread_key, AgentThread.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if mapping:
            await delete_thread_state(thread_key)
            await db.delete(mapping)
            await db.commit()
            session_manager.remove(thread_key)

    return {"ok": True}
