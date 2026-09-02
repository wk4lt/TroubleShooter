import json
import time
from typing import Any, Optional

from pydantic import BaseModel


class AgentEvent(BaseModel):
    type: str
    content: Optional[str] = None
    tool: Optional[str] = None
    result: Optional[Any] = None
    timestamp: float = time.time()

    def to_sse(self) -> str:
        data = self.dict(exclude={"type"})
        return f"event:{self.type}\ndata:{json.dumps(data, ensure_ascii=False)}\n\n"
