from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import settings

_client = AsyncOpenAI(
    base_url=settings.openai_base_url,
    api_key=settings.openai_api_key,
)


class LLMClient:
    def __init__(self):
        self.client = _client
        self.model = settings.openai_model

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> Any:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        return await self.client.chat.completions.create(**kwargs)


llm_client = LLMClient()
