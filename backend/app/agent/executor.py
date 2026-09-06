import asyncio
import contextvars
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


def _tool_intent(name: str, arguments: Dict[str, Any]) -> str:
    if name == "read_skill":
        return "读取 Skill 规范，确认允许的步骤和脚本"
    if name == "run_skill_script":
        script = arguments.get("script") or "Skill 脚本"
        return f"执行 {script}，获取任务所需的真实数据"
    if name == "search_knowledge":
        subsystem = arguments.get("subsystem_id") or "相关子系统"
        return f"检索 {subsystem} 企业知识库，补充设计文档或 SOP 依据"
    if name == "list_files":
        return "检查当前工作区，确认可用输入文件"
    if name == "read_file":
        return "读取工作区文件，提取任务相关内容"
    if name == "write_file":
        return "将分析结果写入工作区文件"
    if name == "get_time":
        return "获取当前时间，校准结果时效性"
    if name == "search_database":
        return "查询结构化数据源，补充事实信息"
    return f"调用 {name}，获取下一步所需信息"


def _tool_result_summary(name: str, output: Any, error: Optional[str]) -> str:
    if error:
        return f"{name} 执行失败：{error}"
    if name == "search_knowledge" and isinstance(output, dict):
        total = output.get("total", len(output.get("results", [])))
        return f"知识检索完成，命中 {total} 条结果，下一步核对引用来源"
    if name == "run_skill_script" and isinstance(output, dict):
        state = "成功" if output.get("ok", True) else "返回异常"
        return f"Skill 脚本{state}，已返回标准输出和错误输出"
    if name == "list_files" and isinstance(output, dict):
        return f"工作区检查完成，发现 {len(output.get('files', []))} 个文件"
    if name == "read_file" and isinstance(output, dict):
        if output.get("truncated"):
            return (
                f"文件读取了第 {output.get('start_line')} 到 {output.get('end_line')} 行，"
                f"内容较大，下一段从第 {output.get('next_start_line')} 行开始"
            )
        return f"文件读取完成，已取得 {output.get('filename', '目标文件')} 内容"
    if isinstance(output, dict):
        keys = list(output.keys())[:4]
        return f"{name} 已返回结果，包含字段：{'、'.join(keys) or '无'}"
    if isinstance(output, list):
        return f"{name} 已返回 {len(output)} 条结果"
    return f"{name} 已返回结果，准备继续判断"


def _run_async_in_thread(coroutine: Any) -> Any:
    context = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(context.run, asyncio.run, coroutine).result()


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
            type="tool_call",
            phase="tool",
            content=_tool_intent(name, arguments),
            tool=name,
            skill=event_skill or None,
            call_id=call["id"],
            arguments=arguments,
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
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        result_event = AgentEvent(
            type="tool_result",
            phase="tool",
            content=_tool_result_summary(name, output, result["error"]),
            tool=name,
            skill=event_skill or None,
            call_id=call["id"],
            result=output,
            duration_ms=round(elapsed_ms, 1),
        )
        events.append({"type": "tool_result", "tool": name, "result": output})
        if event_callback is not None:
            event_callback(result_event)
        messages.append({
            "role": "tool",
            "tool_call_id": result["tool_call_id"],
            "content": compact_tool_output(output),
        })
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
