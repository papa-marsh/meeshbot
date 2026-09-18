from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, TypedDict


class AIModel(StrEnum):
    CHEAP = "cheap"
    BASIC = "basic"
    POWERFUL = "powerful"
    FRONTIER = "frontier"


class AIMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class Context:
    group_id: str
    sender_id: str | None = None
    trigger_message_id: str | None = None


class ToolParameter(TypedDict):
    type: Literal["string"]
    description: str


class ToolSchema(TypedDict):
    type: Literal["object"]
    properties: dict[str, ToolParameter]
    required: list[str]
    additionalProperties: bool


class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: ToolSchema


@dataclass(frozen=True)
class ToolResult:
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class AITool:
    definition: ToolDefinition
    execute: Callable[[dict[str, str]], Awaitable[str]]

    async def invoke(self, arguments: object) -> ToolResult:
        if not isinstance(arguments, dict):
            return ToolResult("Error: tool arguments must be an object.", is_error=True)
        values: dict[str, str] = {}
        for name in self.definition["input_schema"]["required"]:
            value = arguments.get(name)
            if not isinstance(value, str):
                return ToolResult(f"Error: {name} must be a string.", is_error=True)
            values[name] = value
        try:
            content = await self.execute(values)
        except Exception as exc:
            return ToolResult(f"Error: {exc}", is_error=True)
        return ToolResult(content, is_error=content.startswith("Error:"))
