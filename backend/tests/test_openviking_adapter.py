import tempfile
import unittest
from pathlib import Path

from app.context.openviking_adapter import OpenVikingAdapter


class FakeOfficialClient:
    """Mock only the official SDK boundary; it is never used by production code."""

    def __init__(self) -> None:
        self.calls = []

    async def add_resource(self, path, *, to, wait):
        self.calls.append(("add_resource", path, to, wait))
        return {"uri": "viking://resources/troubleshooter/test.md"}

    async def find(self, *, query, target_uri, limit):
        self.calls.append(("find", query, target_uri, limit))
        return {"items": [{"uri": "viking://resources/troubleshooter/test.md"}]}

    async def get_session(self, session_id, *, auto_create):
        self.calls.append(("get_session", session_id, auto_create))
        return {"session_id": session_id}

    async def get_session_context(self, session_id, *, token_budget):
        self.calls.append(("get_session_context", session_id, token_budget))
        return {"context": "official memory"}

    async def add_message(self, session_id, *, role, content):
        self.calls.append(("add_message", session_id, role, content))
        return {"ok": True}

    async def commit_session(self, session_id):
        self.calls.append(("commit_session", session_id))
        return {"ok": True}

    async def close(self):
        self.calls.append(("close",))


class OpenVikingAdapterTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.client = FakeOfficialClient()
        self.adapter = OpenVikingAdapter(client=self.client)

    async def test_import_and_find_delegate_to_official_client(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "official-openviking-smoke.md"
            document.write_text("OpenViking resource import", encoding="utf-8")
            imported = await self.adapter.import_resource(document)

        found = await self.adapter.find("resource import")

        self.assertIn("uri", imported)
        self.assertEqual(1, len(found["items"]))
        self.assertEqual("add_resource", self.client.calls[0][0])
        self.assertEqual("find", self.client.calls[1][0])

    async def test_session_messages_and_commit_delegate_to_official_client(self) -> None:
        await self.adapter.add_message("browser-session", "user", "inspect the incident")
        await self.adapter.add_message("browser-session", "assistant", "root cause found")
        await self.adapter.commit("browser-session")

        operations = [call[0] for call in self.client.calls]
        self.assertEqual(operations.count("get_session"), 3)
        self.assertEqual(operations.count("add_message"), 2)
        self.assertEqual(operations[-1], "commit_session")
