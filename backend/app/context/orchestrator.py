"""Build Agent context exclusively from the official OpenViking service."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.context.openviking_adapter import OpenVikingAdapter, openviking_adapter

class ContextOrchestrator:
    """Orchestrate official OpenViking context for the current Agent runtime."""

    def __init__(self, openviking: OpenVikingAdapter = openviking_adapter) -> None:
        self._openviking = openviking

    async def begin_task(
        self, application_session_id: str, task_input: str
    ) -> List[Dict[str, Any]]:
        """Read official session context, retrieve context, then record the new turn."""
        session_context = await self._openviking.get_session_context(application_session_id)
        openviking_results = await self._openviking.find(task_input)
        await self._openviking.add_message(application_session_id, "user", task_input)

        sources: Dict[str, Any] = {
            "openviking_session": session_context,
            "openviking_find": openviking_results,
        }
        return [{"role": "system", "content": json.dumps(sources, ensure_ascii=False)}]

    async def complete_task(self, application_session_id: str, final_content: str) -> None:
        await self._openviking.add_message(application_session_id, "assistant", final_content)
        await self._openviking.commit(application_session_id)
