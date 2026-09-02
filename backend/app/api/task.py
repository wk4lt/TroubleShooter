import uuid
from typing import Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.agent.loop import start_agent_task
from app.logger import log_event
from app.storage.sessions import sessions

router = APIRouter(prefix="/api/task", tags=["task"])


class CreateTaskRequest(BaseModel):
    input: str
    skill: Optional[str] = None


class CreateTaskResponse(BaseModel):
    task_id: str
    session_id: str


@router.post("", response_model=CreateTaskResponse)
async def create_task(req: CreateTaskRequest, x_session_id: str = Header(default="")):
    session_id = x_session_id or "default"
    session = sessions.get_or_create(session_id)
    task_id = uuid.uuid4().hex[:8]
    state = session.create_task(task_id, req.input, req.skill)
    sessions.index_task(task_id, session_id)
    log_event(
        f"创建任务 {task_id} (skill={req.skill or '-'})",
        level="info",
        source="api",
        session_id=session_id,
        task_id=task_id,
    )
    start_agent_task(session, state)
    return CreateTaskResponse(task_id=task_id, session_id=session_id)


@router.get("/{task_id}")
async def get_task(task_id: str):
    session = sessions.find_by_task(task_id)
    state = session.tasks.get(task_id) if session is not None else None
    if state is None:
        return {"error": "task not found"}
    return {
        "task_id": state.task_id,
        "session_id": state.session_id,
        "status": state.status,
        "result": state.result,
        "events": [e.dict() for e in state.events],
    }
