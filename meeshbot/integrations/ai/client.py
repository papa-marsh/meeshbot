from collections.abc import Mapping, Sequence
from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel

from meeshbot.config import AI_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY, TIMEZONE
from meeshbot.integrations.ai.context import IMAGE_ANALYSIS_CONTEXT, resolve_timestamp_context
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
from meeshbot.integrations.groupme.attachments import render_attachments

DEFAULT_MAX_TOKENS = 2048
ERROR_OUTPUT = "FAILED"


class _ResolvedTimestamp(BaseModel):
    iso: str


class _ImageDescription(BaseModel):
    description: str


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
        attachments: Sequence[Mapping[str, object]] = (),
    ) -> AIMessage:
        timestamp_string = timestamp.astimezone(TIMEZONE).strftime("%b %-d %Y, %-I:%M%p")
        rendered = render_attachments(attachments)
        body = "\n".join(part for part in (message, rendered) if part)
        return AIMessage(
            role="assistant" if sender_name == "MeeshBot" else "user",
            content=f"{sender_name} ({timestamp_string}): {body}",
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
        system = resolve_timestamp_context(now_str, ERROR_OUTPUT)
        result = await self.provider.generate_structured(
            description, context=system, output_format=_ResolvedTimestamp, max_tokens=64
        )
        return result.iso

    async def describe_image(self, url: str) -> str:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Image analysis requires an HTTPS image URL without credentials")
        result = await self.provider.generate_structured(
            "Describe the attached image for the chat history.",
            context=IMAGE_ANALYSIS_CONTEXT,
            output_format=_ImageDescription,
            max_tokens=1024,
            image_url=url,
        )
        description = result.description.strip()
        if not description:
            raise ValueError("Image analysis returned an empty description")
        return description

    async def score_response_likelihood(
        self, history_text: str, context: str
    ) -> ResponseLikelihood:
        return await self.provider.generate_structured(
            history_text, context=context, output_format=ResponseLikelihood, max_tokens=200
        )
