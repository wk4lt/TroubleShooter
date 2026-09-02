import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.logger import log_event
from app.storage.logs import log_store

router = APIRouter(prefix="/api/logs", tags=["logs"])


class ClientLog(BaseModel):
    level: str = "INFO"
    message: str
    source: str = "frontend"
    session_id: str = ""


@router.post("")
async def receive_log(entry: ClientLog):
    log_event(
        entry.message,
        level=entry.level,
        source=entry.source,
        session_id=entry.session_id or None,
    )
    return {"ok": True}


@router.get("")
async def get_logs(
    session_id: str = "",
    level: str = "",
    limit: int = Query(default=200, le=1000),
):
    return {
        "logs": log_store.list(
            session_id or None, level or None, limit
        ),
    }


@router.get("/stream")
async def stream_logs(
    session_id: str = "",
    level: str = "",
    since: int = 0,
):
    async def gen():
        seen = since
        while True:
            for e in log_store.list_after(seen):
                seen = max(seen, e["seq"] + 1)
                if session_id and e.get("session_id") != session_id:
                    continue
                if level and e.get("level") != level.upper():
                    continue
                yield f"data:{json.dumps(e, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.4)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
