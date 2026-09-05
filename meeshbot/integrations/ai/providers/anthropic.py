from collections.abc import Sequence

from anthropic import AsyncAnthropic, omit
from anthropic.types import (
    MessageParam,
    ThinkingConfigParam,
    ToolResultBlockParam,
    ToolUnionParam,
    WebFetchTool20260209Param,
    WebSearchTool20260209Param,
)
from pydantic import BaseModel

from meeshbot.integrations.ai.provider import execute_tool
from meeshbot.integrations.ai.types import AIMessage, AIModel, AITool
from meeshbot.utils.logging import log

MODELS = {
    AIModel.CHEAP: "claude-haiku-4-5",
    AIModel.BASIC: "claude-sonnet-5",
    AIModel.POWERFUL: "claude-opus-5",
    AIModel.FRONTIER: "claude-fable-5-1",
}

# Mandatory adaptive thinking shares the output budget with the answer.
FRONTIER_MIN_TOKENS = 8192


class AnthropicProvider:
    def __init__(self, model: AIModel, *, api_key: str) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the Anthropic provider")
        self.model = MODELS[model]
        self.tier = model
        self.api_key = api_key

    def _max_tokens(self, requested: int) -> int:
        if self.tier == AIModel.FRONTIER:
            return max(requested, FRONTIER_MIN_TOKENS)
        return requested

    async def generate_response(
        self,
        messages: Sequence[AIMessage],
        *,
        context: str,
        max_tokens: int,
        tools: Sequence[AITool],
        allow_web: bool,
    ) -> str:
        conversation: list[MessageParam] = [
            {"role": message["role"], "content": message["content"]} for message in messages
        ]
        native_tools: list[ToolUnionParam] = [
            {
                "name": tool.definition["name"],
                "description": tool.definition["description"],
                "input_schema": dict(tool.definition["input_schema"]),
            }
            for tool in tools
        ]
        if allow_web:
            search: WebSearchTool20260209Param = {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 10,
            }
            fetch: WebFetchTool20260209Param = {
                "type": "web_fetch_20260209",
                "name": "web_fetch",
                "max_uses": 5,
            }
            if self.tier == AIModel.CHEAP:
                search["allowed_callers"] = ["direct"]
                fetch["allowed_callers"] = ["direct"]
            native_tools.extend([search, fetch])

        response_text = ""
        async with AsyncAnthropic(api_key=self.api_key) as client:
            while True:
                response = await client.messages.create(
                    model=self.model,
                    max_tokens=self._max_tokens(max_tokens),
                    system=context,
                    messages=conversation,
                    tools=native_tools,
                    output_config={"effort": "low"} if self.tier == AIModel.FRONTIER else omit,
                )
                text = "".join(block.text for block in response.content if block.type == "text")
                response_text = text or response_text
                log.info(
                    "AI response received",
                    provider="anthropic",
                    model=self.model,
                    stop_reason=response.stop_reason,
                    text=text or None,
                )
                if response.stop_reason == "pause_turn":
                    conversation.append({"role": "assistant", "content": response.content})
                    continue
                if response.stop_reason != "tool_use":
                    return response_text

                conversation.append({"role": "assistant", "content": response.content})
                results: list[ToolResultBlockParam] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    result = await execute_tool(tools, block.name, block.input)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.content,
                            "is_error": result.is_error,
                        }
                    )
                if not results:
                    raise ValueError("Anthropic requested tool use without any tool calls")
                conversation.append({"role": "user", "content": results})

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        *,
        context: str,
        output_format: type[T],
        max_tokens: int,
    ) -> T:
        thinking: ThinkingConfigParam = (
            {"type": "adaptive"} if self.tier == AIModel.FRONTIER else {"type": "disabled"}
        )
        async with AsyncAnthropic(api_key=self.api_key) as client:
            response = await client.messages.parse(
                model=self.model,
                max_tokens=self._max_tokens(max_tokens),
                system=context,
                messages=[{"role": "user", "content": prompt}],
                output_format=output_format,
                thinking=thinking,
                output_config={"effort": "low"} if self.tier == AIModel.FRONTIER else omit,
            )
        if response.parsed_output is None or response.stop_reason != "end_turn":
            raise ValueError(f"Anthropic did not return a complete {output_format.__name__}")
        return response.parsed_output
