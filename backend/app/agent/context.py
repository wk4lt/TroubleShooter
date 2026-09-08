import json
from typing import Any, Dict, List


MAX_TOOL_RESULT_CHARS = 12_000


def compact_tool_output(output: Any, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Keep tool output useful to the model while bounding its context cost."""
    encoded = json.dumps(output, ensure_ascii=False, default=str)
    if len(encoded) <= limit:
        return encoded

    if isinstance(output, dict):
        compact: Dict[str, Any] = {}
        for key, value in output.items():
            if isinstance(value, list):
                compact[key] = value[:20]
                compact[f"{key}_truncated"] = True
                compact[f"{key}_total"] = len(value)
            elif isinstance(value, str):
                compact[key] = value[:2000]
                compact[f"{key}_truncated"] = True
            else:
                compact[key] = value
        encoded = json.dumps(compact, ensure_ascii=False, default=str)
    return encoded[:limit] + "\n[tool result truncated]"


class ContextManager:
    """Build model messages; OpenViking owns session compression and memory."""

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def build_initial(
        self, retrieved_context: List[Dict[str, Any]], task_input: str
    ) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": self.system_prompt},
            *retrieved_context,
            {"role": "user", "content": task_input},
        ]

    def prepare(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return messages
