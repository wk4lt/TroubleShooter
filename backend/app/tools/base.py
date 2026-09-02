from typing import Any, Callable, Dict

from pydantic import BaseModel


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class BaseTool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.spec = ToolSpec(name=name, description=description, parameters=parameters)

    def to_openai_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.spec.name,
                "description": self.spec.description,
                "parameters": self.spec.parameters,
            },
        }

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        raise NotImplementedError


class FunctionTool(BaseTool):
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        super().__init__(name, description, parameters)
        self._func = func

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        result = self._func(**arguments)
        if hasattr(result, "__await__"):
            result = await result
        return result
