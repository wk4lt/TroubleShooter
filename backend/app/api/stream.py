import asyncio
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.storage.sessions import sessions

router = APIRouter(prefix="/api/task", tags=["stream"])


@router.get("/{task_id}/stream")
async def stream_task(task_id: str):
    session = sessions.find_by_task(task_id)
    state = session.tasks.get(task_id) if session is not None else None
    if state is None:
        return {"error": "task not found"}

    cond = session.conditions.get(task_id)

    async def event_stream() -> AsyncIterator[str]:
        cursor = 0
        # Flush the response immediately. This also prevents a proxy from
        # treating a quiet model request as an idle connection.
        yield ": connected\n\n"
        while True:
            pending = []
            finished = False
            heartbeat = False
            async with cond:
                if cursor < len(state.events):
                    pending = list(state.events[cursor:])
                    cursor += len(pending)
                finished = state.status in ("completed", "failed", "cancelled") and not pending
                if not pending and not finished:
                    try:
                        await asyncio.wait_for(cond.wait(), timeout=15)
                    except asyncio.TimeoutError:
                        heartbeat = True

            for event in pending:
                yield event.to_sse()
            if heartbeat:
                yield ": keep-alive\n\n"
            if finished:
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
