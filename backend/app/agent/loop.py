import asyncio
import contextvars
import json
import threading
import time
from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.context import ContextManager
from app.agent.event import AgentEvent
from app.agent.executor import execute_tool_calls_sync
from app.agent.planner import build_system_prompt, get_tool_specs
from app.agent.protocol import ToolCall, normalize_tool_calls
from app.agent.state import AgentState
from app.config import settings
from app.llm.client import llm_client
from app.logger import log_event
from app.storage.context import (
    current_session_id,
    current_skill,
    current_task_id,
    current_workspace_dir,
)
from app.storage.sessions import Session


class GraphState(TypedDict, total=False):
    messages: List[Dict[str, Any]]
    iteration: int
    tool_calls: List[ToolCall]
    tool_events: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    final_content: str
    next_step: Literal["tools", "force_finish", "finish"]


class AgentRuntime:
    """Pure-data LangGraph runtime; Session/SSE side effects stay outside the graph."""

    def __init__(self, session: Session, task_state: AgentState):
        self.session = session
        self.task_state = task_state
        self.max_iterations = max(1, settings.agent_max_iterations)
        self.tool_specs: List[Dict[str, Any]] = []
        self.context_manager: ContextManager | None = None
        self.started_at = 0.0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.model_call_count = 0
        self._summary_logged = False
        self.graph = None

    def _prepare(self) -> None:
        """Load Skill/MCP metadata inside the worker, outside the HTTP loop."""
        self.tool_specs = get_tool_specs(self.task_state.skill)
        self.context_manager = ContextManager(
            build_system_prompt(self.task_state.skill, str(self.session.files.base_dir))
        )
        self.graph = self._build_graph()

    def _usage(self, response: Any) -> tuple[int, int, int]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return 0, 0, 0

        def value(name: str) -> int:
            raw = getattr(usage, name, None)
            if raw is None and isinstance(usage, dict):
                raw = usage.get(name)
            try:
                return int(raw or 0)
            except (TypeError, ValueError):
                return 0

        prompt = value("prompt_tokens")
        completion = value("completion_tokens")
        total = value("total_tokens") or prompt + completion
        return prompt, completion, total

    def _record_model_call(self, response: Any, round_number: int, phase: str, elapsed_ms: float) -> None:
        prompt, completion, total = self._usage(response)
        self.model_call_count += 1
        self.total_prompt_tokens += prompt
        self.total_completion_tokens += completion
        self.total_tokens += total
        log_event(
            f"LLM round={round_number} phase={phase} elapsed_ms={elapsed_ms:.1f} "
            f"prompt_tokens={prompt} completion_tokens={completion} total_tokens={total}",
            source="agent",
            session_id=self.session.session_id,
            task_id=self.task_state.task_id,
        )

    def log_summary(self, status: str) -> None:
        if self._summary_logged:
            return
        self._summary_logged = True
        elapsed_ms = (time.perf_counter() - self.started_at) * 1000 if self.started_at else 0
        log_event(
            f"Agent summary status={status} rounds={self.model_call_count} "
            f"prompt_tokens={self.total_prompt_tokens} completion_tokens={self.total_completion_tokens} "
            f"total_tokens={self.total_tokens} elapsed_ms={elapsed_ms:.1f}",
            source="agent",
            session_id=self.session.session_id,
            task_id=self.task_state.task_id,
        )

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("call_model", self._call_model)
        graph.add_node("execute_tools", self._execute_tools)
        graph.add_node("force_finish", self._force_finish)
        graph.add_node("finish", self._finish)
        graph.add_edge(START, "call_model")
        graph.add_conditional_edges(
            "call_model", lambda state: state["next_step"],
            {"tools": "execute_tools", "force_finish": "force_finish", "finish": "finish"},
        )
        graph.add_edge("execute_tools", "call_model")
        graph.add_edge("force_finish", "finish")
        graph.add_edge("finish", END)
        return graph.compile()

    def _call_model(self, state: GraphState) -> GraphState:
        iteration = state.get("iteration", 0) + 1
        messages = self.context_manager.prepare(state["messages"])
        thinking = (
            "正在理解任务，规划执行路径并选择合适工具"
            if iteration == 1
            else "已收到上一轮工具结果，正在核对证据并决定下一步"
        )
        self.session.publish_from_thread(
            self.task_state.task_id,
            AgentEvent(type="thinking", phase="analysis", content=thinking),
        )
        started_at = time.perf_counter()
        response = llm_client.chat_sync(messages, tools=self.tool_specs)
        self._record_model_call(response, iteration, "tool_decision", (time.perf_counter() - started_at) * 1000)
        message = response.choices[0].message
        calls = normalize_tool_calls(message.tool_calls)
        assistant: Dict[str, Any] = {"role": "assistant", "content": message.content}
        if calls:
            decision = (
                f"本轮计划（第 {iteration}/{self.max_iterations} 轮）："
                + "、".join(f"调用 {call['name']}" for call in calls)
            )
            assistant["tool_calls"] = [
                {
                    "id": call["id"], "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                    },
                }
                for call in calls
            ]
            next_step = "tools" if iteration < self.max_iterations else "force_finish"
        else:
            decision = "证据已足够，正在整理最终答案并保留必要引用"
            next_step = "finish"
        self.session.publish_from_thread(
            self.task_state.task_id,
            AgentEvent(type="thinking", phase="decision", content=decision),
        )
        return {
            "messages": messages + [assistant],
            "iteration": iteration,
            "tool_calls": calls,
            "tool_events": state.get("tool_events", []),
            "events": state.get("events", []) + [{
                "type": "thinking",
                "content": thinking,
            }],
            "final_content": message.content or "",
            "next_step": next_step,
        }

    def _execute_tools(self, state: GraphState) -> GraphState:
        messages, events = execute_tool_calls_sync(
            state.get("tool_calls", []),
            session_id=self.session.session_id,
            task_id=self.task_state.task_id,
            round_number=state.get("iteration", 0),
            event_callback=lambda event: self.session.publish_from_thread(
                self.task_state.task_id, event
            ),
        )
        if any(call["name"] == "read_skill" for call in state.get("tool_calls", [])):
            self.tool_specs = [
                spec for spec in self.tool_specs
                if spec.get("function", {}).get("name") != "read_skill"
            ]
        return {
            "messages": state["messages"] + messages,
            "tool_calls": [],
            "tool_events": state.get("tool_events", []) + events,
            "events": state.get("events", []) + events,
        }

    def _force_finish(self, state: GraphState) -> GraphState:
        self.session.publish_from_thread(
            self.task_state.task_id,
            AgentEvent(
                type="thinking",
                phase="synthesis",
                content="执行轮数达到上限，正在基于已有证据整理最终答案",
            ),
        )
        started_at = time.perf_counter()
        response = llm_client.chat_sync(
            state["messages"] + [{
                "role": "system",
                "content": "执行轮数已达到上限。请基于已有结果总结进展和未完成部分，不要调用工具。",
            }],
            tools=None,
        )
        self._record_model_call(
            response, state.get("iteration", 0), "force_finish", (time.perf_counter() - started_at) * 1000
        )
        return {"final_content": response.choices[0].message.content or "已达到执行上限。"}

    def _finish(self, state: GraphState) -> GraphState:
        return {"final_content": state.get("final_content", "")}

    def _invoke_graph_stream(self, history: List[Dict[str, Any]]) -> GraphState:
        """Run the blocking LangGraph graph in the worker thread."""
        self._prepare()
        assert self.context_manager is not None
        assert self.graph is not None
        initial: GraphState = {
            "messages": self.context_manager.build_initial(history, self.task_state.task_input),
            "iteration": 0,
            "tool_calls": [],
            "tool_events": [],
            "events": [],
            "next_step": "finish",
        }
        result: GraphState = dict(initial)

        for update in self.graph.stream(initial, stream_mode="updates"):
            for node_state in update.values():
                if not isinstance(node_state, dict):
                    continue
                result.update(node_state)

        return result

    async def _invoke_graph_async(self, history: List[Dict[str, Any]]) -> GraphState:
        """Run LangGraph without blocking the FastAPI loop or awaiting its executor."""
        result: Dict[str, GraphState] = {}
        error: Dict[str, Exception] = {}
        finished = threading.Event()
        context = contextvars.copy_context()

        def worker() -> None:
            try:
                result["value"] = context.run(self._invoke_graph_stream, history)
            except Exception as exc:  # noqa: BLE001
                error["value"] = exc
            finally:
                finished.set()

        threading.Thread(
            target=worker,
            name=f"agent-{self.task_state.task_id}",
            daemon=True,
        ).start()
        while not finished.is_set():
            await asyncio.sleep(0.01)
        if "value" in error:
            raise error["value"]
        return result["value"]

    async def run(self) -> None:
        token = current_session_id.set(self.session.session_id)
        skill_token = current_skill.set(self.task_state.skill or "")
        task_token = current_task_id.set(self.task_state.task_id)
        workspace_token = current_workspace_dir.set(str(self.session.files.base_dir))
        self.started_at = time.perf_counter()
        try:
            history = await self.session.history_snapshot()
            if self.task_state.skill:
                await self.session.publish(
                    self.task_state.task_id,
                    AgentEvent(
                        type="thinking",
                        phase="setup",
                        content=f"已加载 Skill：{self.task_state.skill}",
                        skill=self.task_state.skill,
                    ),
                )
            else:
                await self.session.publish(
                    self.task_state.task_id,
                    AgentEvent(
                        type="thinking",
                        phase="setup",
                        content="未指定 Skill，等待模型根据任务选择工具链",
                    ),
                )
            # LLM calls and tool execution are synchronous. Keep them off the
            # FastAPI event loop so task creation and SSE delivery stay responsive.
            result = await self._invoke_graph_async(history)
            self.task_state.status = "completed"
            self.task_state.result = result.get("final_content", "")
            await self.session.append_history(
                {"role": "user", "content": self.task_state.task_input},
                {"role": "assistant", "content": self.task_state.result},
            )
            await self.session.publish(self.task_state.task_id, AgentEvent(type="message", content=self.task_state.result))
            await self.session.publish(
                self.task_state.task_id,
                AgentEvent(type="final", result=self.task_state.result, status="completed"),
            )
            self.log_summary("completed")
        except asyncio.CancelledError:
            self.task_state.status = "cancelled"
            self.task_state.result = "任务已取消"
            self.log_summary("cancelled")
            raise
        except Exception:
            self.log_summary("failed")
            raise
        finally:
            current_task_id.reset(task_token)
            current_workspace_dir.reset(workspace_token)
            current_skill.reset(skill_token)
            current_session_id.reset(token)


def start_agent_task(session: Session, state: AgentState) -> asyncio.Task:
    async def _run() -> None:
        try:
            state.status = "running"
            runtime = AgentRuntime(session, state)
            await runtime.run()
        except Exception as exc:  # noqa: BLE001
            state.status = "failed"
            if not settings.openai_api_key:
                state.result = "执行失败：未配置 OPENAI_API_KEY，请在 backend/.env 中配置后重启服务。"
            elif type(exc).__name__ in {"APIConnectionError", "ConnectError", "TimeoutException"}:
                state.result = "执行失败：无法连接 LLM 服务，请检查网络、代理和 OPENAI_BASE_URL。"
            else:
                state.result = f"执行失败 [{type(exc).__name__}]: {exc}"
            await session.publish(
                state.task_id,
                AgentEvent(type="final", result=state.result, status="failed"),
            )
            log_event(
                f"Agent 执行异常 type={type(exc).__name__} detail={exc} "
                f"model={settings.openai_model} base_url={settings.openai_base_url} "
                f"api_key_configured={bool(settings.openai_api_key)}",
                level="error",
                source="agent",
                session_id=session.session_id,
                task_id=state.task_id,
            )
        finally:
            await session.close(state.task_id)

    return asyncio.create_task(_run())
