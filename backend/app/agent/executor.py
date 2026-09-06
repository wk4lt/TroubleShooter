import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from app.agent.event import AgentEvent
from app.agent.context import compact_tool_output
from app.agent.protocol import ToolCall, ToolResult
from app.logger import log_event
from app.storage.context import current_skill
from app.storage.sessions import Session


def _run_async_in_thread(coroutine: Any) -> Any:
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coroutine).result()


def execute_tool_calls_sync(
    tool_calls: List[ToolCall], session_id: str = "", task_id: str = "", round_number: int = 0,
    event_callback: Optional[Callable[[AgentEvent], None]] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pure synchronous tool executor used inside the LangGraph worker."""
    from app.tools.registry import registry

    messages: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    round_started_at = time.perf_counter()
    for call in tool_calls:
        name = call["name"]
        started_at = time.perf_counter()
        result: ToolResult = {
            "tool_call_id": call["id"], "name": name, "output": None, "error": None
        }
        arguments = call["arguments"]
        event_skill = current_skill.get()
        if name == "read_skill":
            event_skill = str(arguments.get("name") or event_skill or "")
        elif name == "run_skill_script":
            event_skill = str(arguments.get("skill") or event_skill or "")
        call_event = AgentEvent(
            type="tool_call", tool=name, skill=event_skill or None, arguments=arguments
        )
        events.append({"type": "tool_call", "tool": name})
        if event_callback is not None:
            event_callback(call_event)
        tool = registry.get(name)
        if tool is None:
            result["error"] = f"未知工具: {name}"
        else:
            try:
                result["output"] = _run_async_in_thread(tool.execute(call["arguments"]))
            except Exception as exc:  # noqa: BLE001
                result["error"] = str(exc)
        output = result["output"]
        if result["error"] is not None:
            output = {"error": result["error"]}
        result_event = AgentEvent(type="tool_result", tool=name, result=output)
        events.append({"type": "tool_result", "tool": name, "result": output})
        if event_callback is not None:
            event_callback(result_event)
        messages.append({
            "role": "tool",
            "tool_call_id": result["tool_call_id"],
            "content": compact_tool_output(output),
        })
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        log_event(
            f"工具调用 round={round_number} tool={name} elapsed_ms={elapsed_ms:.1f} "
            f"status={'error' if result['error'] else 'ok'}",
            level="error" if result["error"] else "info",
            source="agent",
            session_id=session_id,
            task_id=task_id,
            tool=name,
        )
    log_event(
        f"工具轮次 round={round_number} count={len(tool_calls)} "
        f"elapsed_ms={(time.perf_counter() - round_started_at) * 1000:.1f}",
        source="agent",
        session_id=session_id,
        task_id=task_id,
    )
    return messages, events


async def execute_tool_calls(
    tool_calls: List[ToolCall], session: Session, task_id: str
) -> List[Dict[str, Any]]:
    """Execute normalized calls and return OpenAI-compatible tool messages."""
    from app.tools.registry import registry

    messages: List[Dict[str, Any]] = []
    for call in tool_calls:
        name = call["name"]
        call_id = call["id"]
        await session.publish(task_id, AgentEvent(type="tool_call", tool=name))
        log_event(
            f"调用工具 {name}",
            level="info",
            source="agent",
            session_id=session.session_id,
            task_id=task_id,
            tool=name,
        )

        result: ToolResult = {
            "tool_call_id": call_id,
            "name": name,
            "output": None,
            "error": None,
        }
        tool = registry.get(name)
        if tool is None:
            result["error"] = f"未知工具: {name}"
        else:
            try:
                result["output"] = await tool.execute(call["arguments"])
            except Exception as exc:  # noqa: BLE001
                result["error"] = str(exc)
                log_event(
                    f"工具 {name} 执行异常: {exc}",
                    level="error",
                    source="agent",
                    session_id=session.session_id,
                    task_id=task_id,
                    tool=name,
                )

        output = result["output"]
        if result["error"] is not None:
            output = {"error": result["error"]}
        await session.publish(
            task_id,
            AgentEvent(type="tool_result", tool=name, result=output),
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": result["tool_call_id"],
                "content": compact_tool_output(output),
            }
        )
    return messages
