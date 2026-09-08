import json
import unittest

from app.context.orchestrator import ContextOrchestrator


class FakeOpenViking:
    async def get_session_context(self, session_id: str):
        return {"session_id": session_id, "context": "official memory"}

    async def find(self, query: str):
        return {"resources": [{"uri": "viking://resources/test.md", "query": query}]}

    async def add_message(self, session_id: str, role: str, content: str):
        return {"session_id": session_id, "role": role, "content": content}

    async def commit(self, session_id: str):
        return {"session_id": session_id, "status": "accepted"}


class ContextOrchestratorTest(unittest.IsolatedAsyncioTestCase):
    async def test_begin_task_injects_only_openviking_context(self) -> None:
        orchestrator = ContextOrchestrator(openviking=FakeOpenViking())

        messages = await orchestrator.begin_task("browser-session", "inspect incident")

        sources = json.loads(messages[0]["content"])
        self.assertEqual({"openviking_session", "openviking_find"}, set(sources))
        self.assertNotIn("rca", sources)
