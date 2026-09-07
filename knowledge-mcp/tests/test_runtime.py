from __future__ import annotations

import asyncio
import unittest

from app.config import load_settings
from app.runtime.knowledge_runtime import KnowledgeRuntime


class KnowledgeRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = KnowledgeRuntime(load_settings())

    def test_runbook_search_returns_deployment_first_action(self) -> None:
        result = asyncio.run(
            self.runtime.search_runbook("API 5xx errors after deployment", top_k=1)
        )
        self.assertEqual(result["results"][0]["runbook_id"], "RUNBOOK_HIGH_ERROR_RATE")
        self.assertIn("deployment history", result["results"][0]["procedure"].lower())

    def test_knowledge_base_inventory_is_grouped_by_subsystem(self) -> None:
        result = self.runtime.list_knowledge_bases()
        self.assertIn(
            {"subsystem": "COMMON", "types": ["reference", "runbook"]},
            result["knowledge_bases"],
        )
