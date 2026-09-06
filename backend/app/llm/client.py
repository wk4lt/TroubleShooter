from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI, OpenAI

from app.config import settings
from app.logger import log_event
from app.storage.context import current_session_id, current_task_id

_client = AsyncOpenAI(
    base_url=settings.openai_base_url,
    api_key=settings.openai_api_key,
)
_sync_client = OpenAI(
    base_url=settings.openai_base_url,
    api_key=settings.openai_api_key,
)


class LLMClient:
    def __init__(self):
        self.client = _client
        self.sync_client = _sync_client
        self.model = settings.openai_model

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> Any:
        self._log_request("async", len(messages), len(tools or []))
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        try:
            return await self.client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._log_failure("async", exc)
            raise

    def chat_sync(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> Any:
        self._log_request("sync", len(messages), len(tools or []))
        kwargs: Dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        try:
            return self.sync_client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._log_failure("sync", exc)
            raise

    def _log_request(self, mode: str, message_count: int, tool_count: int) -> None:
        log_event(
            f"LLM request start mode={mode} model={self.model} messages={message_count} "
            f"tools={tool_count} api_key_configured={bool(settings.openai_api_key)}",
            source="llm",
            session_id=current_session_id.get(),
            task_id=current_task_id.get(),
        )

    def _log_failure(self, mode: str, exc: Exception) -> None:
        status_code = getattr(exc, "status_code", None)
        request_id = getattr(exc, "request_id", None)
        log_event(
            f"LLM request failed mode={mode} type={type(exc).__name__} "
            f"status_code={status_code or '-'} request_id={request_id or '-'} "
            f"model={self.model} api_key_configured={bool(settings.openai_api_key)} "
            f"detail={exc}",
            level="error",
            source="llm",
            session_id=current_session_id.get(),
            task_id=current_task_id.get(),
        )


llm_client = LLMClient()
