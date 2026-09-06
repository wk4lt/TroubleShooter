import json
from typing import Any, Dict, List, Optional, TypedDict


class ToolCall(TypedDict):
    id: str
    name: str
    arguments: Dict[str, Any]


class ToolResult(TypedDict):
    tool_call_id: str
    name: str
    output: Any
    error: Optional[str]


def normalize_tool_calls(raw_calls: Any) -> List[ToolCall]:
    """Convert an OpenAI-compatible response into the runtime protocol."""
    calls: List[ToolCall] = []
    for raw_call in raw_calls or []:
        function = raw_call.function
        try:
            arguments = json.loads(function.arguments or "{}")
        except (TypeError, json.JSONDecodeError):
            arguments = {}
        calls.append(
            {
                "id": str(raw_call.id),
                "name": str(function.name),
                "arguments": arguments if isinstance(arguments, dict) else {},
            }
        )
    return calls
