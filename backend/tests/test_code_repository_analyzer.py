import json
import tempfile
import unittest
from pathlib import Path

from app.skills.loader import read_skill
from scripts.import_openviking_demo import collect_document_sources, target_uri


class CodeRepositoryAnalyzerSkillTest(unittest.TestCase):
    def test_skill_is_discoverable_and_has_evidence_contract(self) -> None:
        body = read_skill("code-repository-analyzer")

        self.assertIsNotNone(body)
        self.assertIn("CodeGraph", body)
        self.assertIn("search_knowledge", body)
        self.assertIn("COMPLIANT", body)
        self.assertIn("UNKNOWN", body)

    def test_example_config_allows_codegraph_tools_for_the_skill(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "mcp_servers.example.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        allowed = config["skill_tools"]["code-repository-analyzer"]

        self.assertIn("mcp__codegraph__search", allowed)
        self.assertIn("mcp__codegraph__orient", allowed)
        self.assertIn("mcp__codegraph__path", allowed)
        self.assertIn("mcp__codegraph__refs", allowed)
        self.assertIn("mcp__codegraph__deps", allowed)
        self.assertNotIn("search_knowledge", allowed)  # Built-in tools are not MCP-filtered.

    def test_document_import_selects_docs_not_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Demo", encoding="utf-8")
            (repository / "docs").mkdir()
            (repository / "docs" / "architecture.md").write_text("Architecture", encoding="utf-8")
            (repository / "src").mkdir()
            (repository / "src" / "service.py").write_text("pass", encoding="utf-8")

            sources = collect_document_sources(repository)

        self.assertEqual(["README.md", "docs"], [suffix for _, suffix in sources])
        self.assertEqual(
            "viking://resources/openviking-demo/docs",
            target_uri("viking://resources/openviking-demo", "docs"),
        )
