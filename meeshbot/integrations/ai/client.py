from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel

from meeshbot.config import AI_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY, TIMEZONE
from meeshbot.integrations.ai.provider import AIProvider
from meeshbot.integrations.ai.providers.anthropic import AnthropicProvider
from meeshbot.integrations.ai.providers.openai import OpenAIProvider
from meeshbot.integrations.ai.tools import (
    CREATE_REMINDER_TOOL,
    DB_QUERY_TOOL,
    ReminderContext,
    execute_create_reminder,
    execute_db_query,
)
from meeshbot.integrations.ai.types import AIMessage, AIModel, AITool

DEFAULT_MAX_TOKENS = 2048
ERROR_OUTPUT = "FAILED"


class _ResolvedTimestamp(BaseModel):
    iso: str


class ResponseLikelihood(BaseModel):
    reason: str
    score: int


class AIClient:
    def __init__(self, model: AIModel = AIModel.POWERFUL) -> None:
        self.provider: AIProvider
        match AI_PROVIDER:
            case "anthropic":
                self.provider = AnthropicProvider(model, api_key=ANTHROPIC_API_KEY)
            case "openai":
                self.provider = OpenAIProvider(model, api_key=OPENAI_API_KEY)
            case _:
                raise ValueError(f"Unknown AI_PROVIDER: {AI_PROVIDER!r}")

    @classmethod
    def build_message_history_entry(
        cls,
        sender_name: str,
        timestamp: datetime,
        message: str,
    ) -> AIMessage:
        timestamp_string = timestamp.astimezone(TIMEZONE).strftime("%b %-d %Y, %-I:%M%p")
        return AIMessage(
            role="assistant" if sender_name == "MeeshBot" else "user",
            content=f"{sender_name} ({timestamp_string}): {message}",
        )

    async def generate_response(
        self,
        messages: Sequence[AIMessage],
        context: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        allow_webfetch: bool = True,
        allow_db_query: bool = True,
        reminder_context: ReminderContext | None = None,
    ) -> str:
        tools: list[AITool] = []
        if allow_db_query:

            async def query_database(arguments: dict[str, str]) -> str:
                return await execute_db_query(arguments["sql"])

            tools.append(AITool(DB_QUERY_TOOL, query_database))
        if reminder_context is not None:

            async def create_reminder(arguments: dict[str, str]) -> str:
                return await execute_create_reminder(
                    reminder_context, arguments["time"], arguments["message"]
                )

            tools.append(AITool(CREATE_REMINDER_TOOL, create_reminder))

        return await self.provider.generate_response(
            messages,
            context=context or "",
            max_tokens=max_tokens,
            tools=tools,
            allow_web=allow_webfetch,
        )

    async def resolve_timestamp(self, description: str) -> str:
        now_str = datetime.now(tz=TIMEZONE).strftime("%A, %B %d, %Y %I:%M %p %Z")
        system = (
            f"You are a precise datetime parser. The current date and time is {now_str}. "
            "When given a natural-language date or time description, resolve it to a specific "
            "datetime. Return it in the iso field as an ISO 8601 string "
            "(YYYY-MM-DDTHH:MM:SS) with no timezone suffix. "
            "For vague times of day, use a reasonable default "
            "(morning=09:00, afternoon=14:00, evening=18:00, night=21:00). "
            "For dates with no time specified, use 10:00. "
            f"If the input cannot be resolved to a timestamp, set iso to {ERROR_OUTPUT!r}."
        )
        result = await self.provider.generate_structured(
            description, context=system, output_format=_ResolvedTimestamp, max_tokens=64
        )
        return result.iso

    async def score_response_likelihood(
        self, history_text: str, context: str
    ) -> ResponseLikelihood:
        return await self.provider.generate_structured(
            history_text, context=context, output_format=ResponseLikelihood, max_tokens=200
        )
