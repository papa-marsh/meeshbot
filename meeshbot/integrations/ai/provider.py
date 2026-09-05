from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel

from meeshbot.integrations.ai.types import AIMessage, AITool, ToolResult


class AIProvider(Protocol):
    async def generate_response(
        self,
        messages: Sequence[AIMessage],
        *,
        context: str,
        max_tokens: int,
        tools: Sequence[AITool],
        allow_web: bool,
    ) -> str: ...

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        *,
        context: str,
        output_format: type[T],
        max_tokens: int,
    ) -> T: ...


async def execute_tool(tools: Sequence[AITool], name: str, arguments: object) -> ToolResult:
    for tool in tools:
        if tool.definition["name"] == name:
            return await tool.invoke(arguments)
    return ToolResult(f"Error: tool {name!r} is not available.", is_error=True)
