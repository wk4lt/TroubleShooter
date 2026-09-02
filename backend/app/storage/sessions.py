import asyncio
import time
from typing import Dict, List, Optional

from app.agent.event import AgentEvent
from app.agent.state import AgentState
from app.storage.files import FileStore


class Session:
    """An isolated workspace: own files, own conversation history, own tasks."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.files = FileStore(session_id)
        self.history: List[Dict] = []
        self.tasks: Dict[str, AgentState] = {}
        self.conditions: Dict[str, asyncio.Condition] = {}
        self.last_activity = time.time()

    def touch(self) -> None:
        self.last_activity = time.time()

    def create_task(self, task_id: str, task_input: str, skill: Optional[str] = None) -> AgentState:
        self.touch()
        state = AgentState(task_id, task_input, self.session_id, skill)
        self.tasks[task_id] = state
        self.conditions[task_id] = asyncio.Condition()
        return state

    async def publish(self, task_id: str, event: AgentEvent) -> None:
        state = self.tasks.get(task_id)
        if state is not None:
            state.add_event(event)
        cond = self.conditions.get(task_id)
        if cond is not None:
            async with cond:
                cond.notify_all()

    async def close(self, task_id: str) -> None:
        cond = self.conditions.get(task_id)
        if cond is not None:
            async with cond:
                cond.notify_all()

    def has_running_tasks(self) -> bool:
        return any(t.status in ("pending", "running") for t in self.tasks.values())

    def cleanup(self) -> None:
        self.files.clear()
        self.history.clear()
        self.tasks.clear()
        self.conditions.clear()


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._task_index: Dict[str, str] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id)
        self._sessions[session_id].touch()
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session is not None:
            session.touch()
        return session

    def index_task(self, task_id: str, session_id: str) -> None:
        self._task_index[task_id] = session_id

    def find_by_task(self, task_id: str) -> Optional[Session]:
        sid = self._task_index.get(task_id)
        if sid is None:
            return None
        session = self._sessions.get(sid)
        if session is not None:
            session.touch()
        return session

    def remove(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        session.cleanup()
        for tid in [t for t, s in self._task_index.items() if s == session_id]:
            del self._task_index[tid]
        return True

    def cleanup_expired(self, ttl: float) -> int:
        now = time.time()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_activity > ttl and not s.has_running_tasks()
        ]
        for sid in expired:
            self.remove(sid)
        return len(expired)


sessions = SessionStore()
