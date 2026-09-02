import asyncio
from typing import Any, Dict, List

from app.agent.event import AgentEvent
from app.agent.executor import execute_tool_calls
from app.agent.planner import build_system_prompt, get_tool_specs
from app.agent.state import AgentState
from app.config import settings
from app.llm.client import llm_client
from app.logger import log_event
from app.storage.context import current_session_id
from app.storage.sessions import Session


class AgentLoop:
    def __init__(self, session: Session, state: AgentState):
        self.session = session
        self.state = state
        self.max_iterations = settings.agent_max_iterations

    async def _emit(self, event: AgentEvent) -> None:
        await self.session.publish(self.state.task_id, event)

    async def run(self) -> None:
        token = current_session_id.set(self.session.session_id)
        try:
            await self._run_loop()
        finally:
            current_session_id.reset(token)

    async def _run_loop(self) -> None:
        state = self.state
        await self._emit(AgentEvent(type="thinking", content="正在分析用户任务"))
        state.status = "running"
        log_event(
            "Agent 开始执行任务",
            level="info",
            source="agent",
            session_id=self.session.session_id,
            task_id=state.task_id,
        )

        self.session.history.append({"role": "user", "content": state.task_input})
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(state.skill)},
            *list(self.session.history),
        ]
        tools = get_tool_specs()

        for iteration in range(self.max_iterations):
            response = await llm_client.chat(messages, tools=tools)
            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                log_event(
                    f"LLM 第 {iteration + 1} 轮返回工具调用",
                    level="info",
                    source="agent",
                    session_id=self.session.session_id,
                    task_id=state.task_id,
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    }
                )
                tool_results = await execute_tool_calls(
                    message.tool_calls, self.session, state.task_id
                )
                messages.extend(tool_results)
                await self._emit(AgentEvent(type="thinking", content="继续分析工具结果"))
                continue

            content = message.content or ""
            await self._emit(AgentEvent(type="message", content=content))
            state.result = content
            self.session.history.append({"role": "assistant", "content": content})
            await self._emit(AgentEvent(type="final", result=content))
            state.status = "completed"
            log_event(
                "Agent 任务完成",
                level="info",
                source="agent",
                session_id=self.session.session_id,
                task_id=state.task_id,
            )
            return

        await self._emit(AgentEvent(type="final", result="达到最大迭代次数,任务未完成"))
        state.status = "failed"
        log_event(
            "Agent 达到最大迭代次数,任务失败",
            level="warning",
            source="agent",
            session_id=self.session.session_id,
            task_id=state.task_id,
        )


def start_agent_task(session: Session, state: AgentState) -> asyncio.Task:
    loop = AgentLoop(session, state)

    async def _run() -> None:
        try:
            await loop.run()
        except Exception as exc:  # noqa: BLE001
            await session.publish(
                state.task_id, AgentEvent(type="final", result=f"执行异常: {exc}")
            )
            state.status = "failed"
            log_event(
                f"Agent 执行异常: {exc}",
                level="error",
                source="agent",
                session_id=session.session_id,
                task_id=state.task_id,
            )
        finally:
            await session.close(state.task_id)

    return asyncio.create_task(_run())
