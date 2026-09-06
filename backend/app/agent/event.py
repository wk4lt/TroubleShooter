import json
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    type: str
    phase: Optional[str] = None
    status: Optional[str] = None
    content: Optional[str] = None
    tool: Optional[str] = None
    skill: Optional[str] = None
    call_id: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    duration_ms: Optional[float] = None
    timestamp: float = Field(default_factory=time.time)

    def to_sse(self) -> str:
        data = self.dict(exclude={"type"})
        return f"event:{self.type}\ndata:{json.dumps(data, ensure_ascii=False)}\n\n"
