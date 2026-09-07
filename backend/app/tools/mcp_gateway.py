import asyncio
import json
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
        public_name = remote_name if server.get("expose_unprefixed") else f"mcp__{server['name']}__{remote_name}"
        super().__init__(public_name, description, parameters)
        self.is_mcp = True
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


async def _streamable_http_request(
    server: Dict[str, Any], method: str, params: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> tuple[Dict[str, Any], Optional[str]]:
    """Minimal MCP Streamable HTTP client kept compatible with Python 3.9.

    The Agent process intentionally does not import the Knowledge MCP's RAG
    dependencies.  It only speaks the stable MCP JSON-RPC transport.
    """
    import httpx

    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-03-26",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        response = await client.post(server["url"], headers=headers, json=body)
        response.raise_for_status()
    next_session_id = response.headers.get("Mcp-Session-Id", session_id)
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        messages = [
            line[5:].strip() for line in response.text.splitlines()
            if line.startswith("data:") and line[5:].strip()
        ]
        payload = json.loads(messages[-1]) if messages else {}
    else:
        payload = response.json()
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload.get("result", {}), next_session_id


async def _open_http_session(server: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    _, session_id = await _streamable_http_request(
        server,
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "troubleshooter-agent-runtime", "version": "1.0"},
        },
    )
    if not session_id:
        raise RuntimeError("MCP Streamable HTTP server did not return a session ID")
    await _streamable_http_notification(server, "notifications/initialized", session_id)
    tools, _ = await _streamable_http_request(server, "tools/list", session_id=session_id)
    return tools, session_id


async def _streamable_http_notification(server: Dict[str, Any], method: str, session_id: str) -> None:
    import httpx

    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-03-26",
        "Mcp-Session-Id": session_id,
    }
    body = {"jsonrpc": "2.0", "method": method}
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        response = await client.post(server["url"], headers=headers, json=body)
        response.raise_for_status()


class StreamableHTTPMCPTool(BaseTool):
    def __init__(
        self, server: Dict[str, Any], remote_name: str, description: str, parameters: Dict[str, Any]
    ):
        public_name = remote_name if server.get("expose_unprefixed") else f"mcp__{server['name']}__{remote_name}"
        super().__init__(public_name, description, parameters)
        self.is_mcp = True
        self.server = server
        self.remote_name = remote_name

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        _, session_id = await _open_http_session(self.server)
        result, _ = await _streamable_http_request(
            self.server, "tools/call", {"name": self.remote_name, "arguments": arguments}, session_id
        )
        return _result_to_json(result)


def _result_to_json(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        content = result.get("content", []) or []
        texts = [item.get("text", "") for item in content if item.get("type") == "text"]
        structured = result.get("structuredContent")
        if structured is None and len(texts) == 1:
            try:
                structured = json.loads(texts[0])
            except (TypeError, ValueError):
                pass
        if structured is not None:
            return {"structured": structured, "text": "\n".join(texts)}
        return {"text": "\n".join(texts)}
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
            try:
                if server.get("transport") == "streamable_http":
                    discovered = _run_async(self._discover_http(server))
                else:
                    discovered = _run_async(self._discover(server))
            except Exception:
                # A configured optional server must not prevent the Agent
                # Runtime from serving unrelated tasks while it is offline.
                continue
            for tool in discovered:
                remote_name = tool["name"] if isinstance(tool, dict) else tool.name
                allowed = server.get("allowed_tools")
                if allowed and remote_name not in allowed:
                    continue
                description = (
                    tool.get("description", "") if isinstance(tool, dict)
                    else tool.description or f"MCP tool from {server['name']}"
                )
                parameters = (
                    tool.get("inputSchema", {"type": "object", "properties": {}})
                    if isinstance(tool, dict) else tool.inputSchema or {"type": "object", "properties": {}}
                )
                tool_class = StreamableHTTPMCPTool if server.get("transport") == "streamable_http" else MCPTool
                registry.register(
                    tool_class(server, remote_name, description, parameters)
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

    async def _discover_http(self, server: Dict[str, Any]) -> List[Dict[str, Any]]:
        result, _ = await _open_http_session(server)
        return list(result.get("tools", []))

    def allowed_tool_names(self, skill: Optional[str]) -> Optional[set[str]]:
        configured = self.skill_tools.get(skill or "")
        if not configured:
            return None
        return set(configured)


mcp_manager = MCPManager()
