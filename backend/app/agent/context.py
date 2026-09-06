import json
import re
from typing import Any, Dict, List


CONTEXT_LIMIT = 128_000
TARGET_LIMIT = 96_000
OUTPUT_RESERVE = 12_000
COMPACTION_TRIGGER = TARGET_LIMIT - OUTPUT_RESERVE
RECENT_MESSAGE_COUNT = 12
MAX_WORKING_MEMORY_CHARS = 12_000
MAX_TOOL_RESULT_CHARS = 12_000


def estimate_tokens(value: Any) -> int:
    """Conservative token estimate without adding a tokenizer dependency."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    other = len(text) - cjk
    return max(1, int(cjk * 1.5 + other / 4))


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
    """Build and compact model messages while preserving the task contract."""

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def build_initial(self, history: List[Dict[str, Any]], task_input: str) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": self.system_prompt},
            *history,
            {"role": "user", "content": task_input},
        ]

    def prepare(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if estimate_tokens(messages) + OUTPUT_RESERVE <= COMPACTION_TRIGGER:
            return messages
        return self._compact(messages)

    def _compact(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(messages) <= RECENT_MESSAGE_COUNT + 1:
            return messages
        immutable = messages[0]
        dropped = messages[1:-RECENT_MESSAGE_COUNT]
        recent = messages[-RECENT_MESSAGE_COUNT:]
        memory_lines: List[str] = []
        for message in dropped:
            role = message.get("role", "unknown")
            content = str(message.get("content", ""))
            if content:
                memory_lines.append(f"[{role}] {content[:1000]}")
        memory = "\n".join(memory_lines)[-MAX_WORKING_MEMORY_CHARS:]
        working_memory = {
            "role": "system",
            "content": (
                "以下是较早消息形成的工作记忆，仅包含已出现的信息；"
                "如与最近消息冲突，以最近消息为准：\n" + memory
            ),
        }
        return [immutable, working_memory, *recent]
