import json
from typing import Any, Dict, List

from app.agent.event import AgentEvent
from app.logger import log_event
from app.storage.sessions import Session


async def execute_tool_calls(tool_calls: List[Any], session: Session, task_id: str) -> List[Dict[str, Any]]:
    from app.tools.registry import registry

    results: List[Dict[str, Any]] = []
    for tool_call in tool_calls:
        name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments or "{}")

        await session.publish(task_id, AgentEvent(type="tool_call", tool=name))
        log_event(
            f"调用工具 {name}",
            level="info",
            source="agent",
            session_id=session.session_id,
            task_id=task_id,
            tool=name,
        )

        tool = registry.get(name)
        if tool is None:
            output = {"error": f"未知工具: {name}"}
        else:
            try:
                output = await tool.execute(arguments)
            except Exception as exc:  # noqa: BLE001
                output = {"error": str(exc)}
                log_event(
                    f"工具 {name} 执行异常: {exc}",
                    level="error",
                    source="agent",
                    session_id=session.session_id,
                    task_id=task_id,
                    tool=name,
                )

        await session.publish(
            task_id,
            AgentEvent(type="tool_result", tool=name, result=output),
        )
        log_event(
            f"工具 {name} 返回结果",
            level="info",
            source="agent",
            session_id=session.session_id,
            task_id=task_id,
            tool=name,
        )

        results.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(output, ensure_ascii=False),
            }
        )
    return results
