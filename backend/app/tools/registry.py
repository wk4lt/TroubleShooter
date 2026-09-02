from typing import Any, Callable, Dict, List, Optional

from app.tools.base import BaseTool, FunctionTool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.spec.name] = tool

    def tool(self, name: str, description: str, parameters: Dict[str, Any]) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.register(FunctionTool(name, description, parameters, func))
            return func

        return decorator

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def all_specs(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def names(self) -> List[str]:
        return list(self._tools.keys())


registry = ToolRegistry()
