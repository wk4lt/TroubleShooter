import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool
from app.tools.registry import registry


def _run_async(coroutine: Any) -> Any:
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coroutine).result()


class MCPTool(BaseTool):
    def __init__(
        self,
        server: Dict[str, Any],
        remote_name: str,
        description: str,
        parameters: Dict[str, Any],
    ):
        public_name = f"mcp__{server['name']}__{remote_name}"
        super().__init__(public_name, description, parameters)
        self.server = server
        self.remote_name = remote_name

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        env = os.environ.copy()
        env.update(self.server.get("env", {}))
        params = StdioServerParameters(
            command=self.server["command"],
            args=self.server.get("args", []),
            env=env,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(self.remote_name, arguments)
                return _result_to_json(result)


def _result_to_json(result: Any) -> Dict[str, Any]:
    content: List[Any] = getattr(result, "content", []) or []
    texts = [item.text for item in content if hasattr(item, "text")]
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return {"structured": structured, "text": "\n".join(texts)}
    return {"text": "\n".join(texts)}


class MCPManager:
    def __init__(self, config_path: Optional[str] = None):
        default_path = str(Path(__file__).resolve().parents[2] / "mcp_servers.json")
        self.config_path = Path(config_path or os.getenv("MCP_SERVERS_CONFIG", default_path))
        self.skill_tools: Dict[str, List[str]] = {}
        self.initialized = False

    def initialize(self) -> None:
        if self.initialized:
            return
        self.initialized = True
        if not self.config_path.exists():
            return
        import json

        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.skill_tools = config.get("skill_tools", {})
        for raw_server in config.get("servers", []):
            server = dict(raw_server)
            for tool in _run_async(self._discover(server)):
                remote_name = tool.name
                allowed = server.get("allowed_tools")
                if allowed and remote_name not in allowed:
                    continue
                registry.register(
                    MCPTool(
                        server,
                        remote_name,
                        tool.description or f"MCP tool from {server['name']}",
                        tool.inputSchema or {"type": "object", "properties": {}},
                    )
                )

    async def _discover(self, server: Dict[str, Any]) -> List[Any]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        env = os.environ.copy()
        env.update(server.get("env", {}))
        params = StdioServerParameters(
            command=server["command"], args=server.get("args", []), env=env
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return list((await session.list_tools()).tools)

    def allowed_tool_names(self, skill: Optional[str]) -> Optional[set[str]]:
        configured = self.skill_tools.get(skill or "")
        if not configured:
            return None
        return set(configured)


mcp_manager = MCPManager()
