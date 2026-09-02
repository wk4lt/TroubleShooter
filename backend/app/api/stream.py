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
        while True:
            async with cond:
                while cursor < len(state.events):
                    yield state.events[cursor].to_sse()
                    cursor += 1
                if state.status in ("completed", "failed") and cursor >= len(state.events):
                    break
                await cond.wait()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
