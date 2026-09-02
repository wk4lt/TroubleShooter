from typing import Any, List, Optional

from app.agent.event import AgentEvent


class AgentState:
    def __init__(self, task_id: str, task_input: str, session_id: str = "", skill: Optional[str] = None):
        self.task_id = task_id
        self.task_input = task_input
        self.session_id = session_id
        self.skill = skill
        self.status = "pending"
        self.events: List[AgentEvent] = []
        self.messages: List[str] = []
        self.result: Optional[Any] = None

    def add_event(self, event: AgentEvent) -> None:
        self.events.append(event)

    def add_message(self, message: str) -> None:
        self.messages.append(message)
