import json
from collections.abc import Sequence
from typing import cast

from openai import AsyncOpenAI
from openai.types.responses import Response, ResponseInputItemParam, ResponseInputParam, ToolParam
from openai.types.shared_params import Reasoning
from pydantic import BaseModel

from meeshbot.integrations.ai.provider import execute_tool
from meeshbot.integrations.ai.types import AIMessage, AIModel, AITool, ToolResult
from meeshbot.utils.logging import log

MODELS = {
    AIModel.CHEAP: "gpt-5.6-luna",
    AIModel.BASIC: "gpt-5.6-terra",
    AIModel.POWERFUL: "gpt-5.6-sol",
    AIModel.FRONTIER: "gpt-6-astra",
}

# Mandatory reasoning shares the output budget with the answer.
FRONTIER_MIN_TOKENS = 8192


def _response_text(response: Response) -> str:
    parts: list[str] = []
    for item in response.output:
        if item.type != "message":
            continue
        for content in item.content:
            if content.type == "refusal":
                parts.append(content.refusal)
                continue
            text = content.text
            citations = [a for a in content.annotations if a.type == "url_citation"]
            for citation in sorted(citations, key=lambda a: a.end_index, reverse=True):
                text = (
                    text[: citation.end_index] + f" ({citation.url})" + text[citation.end_index :]
                )
            parts.append(text)
    return "".join(parts)


class OpenAIProvider:
    def __init__(self, model: AIModel, *, api_key: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
        self.model = MODELS[model]
        self.tier = model
        self.api_key = api_key

    def _max_tokens(self, requested: int) -> int:
        if self.tier == AIModel.FRONTIER:
            return max(requested, FRONTIER_MIN_TOKENS)
        return requested

    def _reasoning(self) -> Reasoning:
        return {"effort": "low" if self.tier == AIModel.FRONTIER else "none"}

    async def generate_response(
        self,
        messages: Sequence[AIMessage],
        *,
        context: str,
        max_tokens: int,
        tools: Sequence[AITool],
        allow_web: bool,
    ) -> str:
        conversation: ResponseInputParam = [
            {"role": message["role"], "content": message["content"]} for message in messages
        ]
        native_tools: list[ToolParam] = [
            {
                "type": "function",
                "name": tool.definition["name"],
                "description": tool.definition["description"],
                "parameters": dict(tool.definition["input_schema"]),
                "strict": True,
            }
            for tool in tools
        ]
        if allow_web:
            native_tools.append({"type": "web_search"})
        response_text = ""
        async with AsyncOpenAI(api_key=self.api_key) as client:
            while True:
                response = await client.responses.create(
                    model=self.model,
                    instructions=context,
                    input=conversation,
                    tools=native_tools,
                    max_output_tokens=self._max_tokens(max_tokens),
                    reasoning=self._reasoning(),
                    store=False,
                    include=["reasoning.encrypted_content"],
                )
                log.info(
                    "AI response received",
                    provider="openai",
                    model=self.model,
                    status=response.status,
                    text=response.output_text or None,
                )
                if response.status != "completed" or response.error is not None:
                    raise ValueError(f"OpenAI response did not complete: {response.status}")
                response_text = _response_text(response) or response_text
                calls = [item for item in response.output if item.type == "function_call"]
                if not calls:
                    return response_text

                # Replay all native items, including encrypted reasoning, in stateless requests.
                conversation.extend(
                    cast(ResponseInputItemParam, item.model_dump(exclude_none=True, by_alias=True))
                    for item in response.output
                )
                for call in calls:
                    try:
                        arguments = json.loads(call.arguments)
                    except json.JSONDecodeError:
                        result = ToolResult(
                            "Error: tool arguments must be valid JSON.", is_error=True
                        )
                    else:
                        result = await execute_tool(tools, call.name, arguments)
                    conversation.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": result.content,
                        }
                    )

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        *,
        context: str,
        output_format: type[T],
        max_tokens: int,
    ) -> T:
        async with AsyncOpenAI(api_key=self.api_key) as client:
            response = await client.responses.parse(
                model=self.model,
                instructions=context,
                input=[{"role": "user", "content": prompt}],
                text_format=output_format,
                max_output_tokens=self._max_tokens(max_tokens),
                reasoning=self._reasoning(),
                store=False,
            )
        if (
            response.status != "completed"
            or response.error is not None
            or response.output_parsed is None
        ):
            raise ValueError(f"OpenAI did not return a complete {output_format.__name__}")
        return response.output_parsed
