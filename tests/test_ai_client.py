import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from meeshbot.config import TIMEZONE
from meeshbot.integrations.ai import chat, client
from meeshbot.integrations.ai.client import AIClient, ResponseLikelihood
from meeshbot.integrations.ai.provider import AIProvider, execute_tool
from meeshbot.integrations.ai.providers.anthropic import AnthropicProvider
from meeshbot.integrations.ai.providers.openai import OpenAIProvider
from meeshbot.integrations.ai.tools import DB_QUERY_TOOL, ReminderContext
from meeshbot.integrations.ai.types import AIMessage, AIModel, AITool
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from tests.test_ai_providers import install_api, response_payload, text_output, tool_call


@pytest.mark.parametrize(
    "provider, expected", [("anthropic", AnthropicProvider), ("openai", OpenAIProvider)]
)
def test_only_selected_provider_requires_credentials(
    monkeypatch: pytest.MonkeyPatch, provider: str, expected: type[AIProvider]
) -> None:
    monkeypatch.setattr(client, "AI_PROVIDER", provider)
    monkeypatch.setattr(client, "ANTHROPIC_API_KEY", "test" if provider == "anthropic" else "")
    monkeypatch.setattr(client, "OPENAI_API_KEY", "test" if provider == "openai" else "")
    assert isinstance(AIClient().provider, expected)
    monkeypatch.setattr(client, f"{provider.upper()}_API_KEY", "")
    with pytest.raises(ValueError):
        AIClient()


def test_unknown_provider_fails_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "AI_PROVIDER", "typo")
    with pytest.raises(ValueError):
        AIClient()


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_reminder_identity_is_bound_server_side_and_database_is_not_available(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    requests: list[dict[str, object]] = []
    adapter = install_api(
        monkeypatch,
        provider,
        [
            response_payload(
                provider,
                [
                    tool_call(
                        provider,
                        "create_reminder",
                        {
                            "time": "tomorrow",
                            "message": "buy milk",
                            "group_id": "attacker-group",
                            "sender_id": "attacker",
                        },
                        "call_reminder",
                    ),
                    tool_call(provider, "query_database", {"sql": "SELECT 1"}, "call_database"),
                ],
                status="tools",
            ),
            response_payload(provider, [text_output(provider, "Reminder created.")]),
        ],
        requests,
    )
    monkeypatch.setattr(client, "AI_PROVIDER", provider)
    monkeypatch.setattr(client, "AnthropicProvider", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(client, "OpenAIProvider", lambda *_args, **_kwargs: adapter)
    reminder = AsyncMock(return_value="Reminder created.")
    database = AsyncMock()
    monkeypatch.setattr(client, "execute_create_reminder", reminder)
    monkeypatch.setattr(client, "execute_db_query", database)
    identity = ReminderContext("real-group", "real-sender", "real-message")
    result = asyncio.run(
        AIClient().generate_response(
            [],
            allow_webfetch=False,
            allow_db_query=False,
            reminder_context=identity,
        )
    )
    assert result == "Reminder created."
    reminder.assert_awaited_once_with(identity, "tomorrow", "buy milk")
    database.assert_not_awaited()
    assert [tool["name"] for tool in requests[0]["tools"]] == ["create_reminder"]


@pytest.mark.parametrize("arguments", [None, [], {"sql": 5}, {}])
def test_malformed_tool_arguments_never_reach_executor(arguments: object) -> None:
    execute = AsyncMock()
    result = asyncio.run(
        execute_tool([AITool(DB_QUERY_TOOL, execute)], "query_database", arguments)
    )
    assert result.is_error
    execute.assert_not_awaited()


def test_tool_failure_is_returned_to_model() -> None:
    execute = AsyncMock(side_effect=RuntimeError("database unavailable"))
    result = asyncio.run(
        execute_tool([AITool(DB_QUERY_TOOL, execute)], "query_database", {"sql": "SELECT 1"})
    )
    assert result.is_error
    assert result.content.startswith("Error:")


def test_history_preserves_speaker_and_local_time() -> None:
    timestamp = datetime(2026, 9, 5, 16, tzinfo=UTC)
    human = AIClient.build_message_history_entry("Marshall", timestamp, "hello")
    bot = AIClient.build_message_history_entry("MeeshBot", timestamp, "hi")
    local = timestamp.astimezone(TIMEZONE).strftime("%b %-d %Y, %-I:%M%p")
    assert human == {"role": "user", "content": f"Marshall ({local}): hello"}
    assert bot == {"role": "assistant", "content": f"MeeshBot ({local}): hi"}


@pytest.mark.parametrize("score, expected", [(49, False), (50, True)])
def test_classifier_sees_transcript_as_evidence_and_applies_threshold(
    monkeypatch: pytest.MonkeyPatch, score: int, expected: bool
) -> None:
    history: list[AIMessage] = [
        {"role": "assistant", "content": "MeeshBot: hi"},
        {"role": "user", "content": "Marshall: question"},
    ]
    monkeypatch.setattr(chat, "build_message_history", AsyncMock(return_value=history))
    score_call = AsyncMock(return_value=ResponseLikelihood(reason="Addressed", score=score))
    monkeypatch.setattr(client.AIClient, "score_response_likelihood", score_call)
    monkeypatch.setattr(client, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(client, "ANTHROPIC_API_KEY", "test")
    assert asyncio.run(chat.should_respond("group")) is expected
    prompt = score_call.call_args.kwargs["history_text"]
    assert prompt.startswith("MeeshBot: hi")
    assert prompt.endswith("--- The message you are evaluating is: ---\n\nMarshall: question")


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("text", ["", "hello"])
def test_chat_controls_database_access_and_skips_empty_posts(
    monkeypatch: pytest.MonkeyPatch, public: bool, text: str
) -> None:
    monkeypatch.setattr(chat, "build_message_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat, "is_public_group", lambda _group: public)
    monkeypatch.setattr(client, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(client, "ANTHROPIC_API_KEY", "test")
    generate = AsyncMock(return_value=text)
    post = AsyncMock()
    monkeypatch.setattr(client.AIClient, "generate_response", generate)
    monkeypatch.setattr(chat.GroupMeClient, "post_message", post)
    trigger = GroupMeWebhookPayload.model_construct(id="msg", user_id="sender")
    asyncio.run(chat.send_ai_response("group", trigger=trigger))
    assert generate.call_args.kwargs["allow_db_query"] is not public
    assert generate.call_args.kwargs["reminder_context"] == ReminderContext(
        "group", "sender", "msg"
    )
    if text:
        post.assert_awaited_once_with(group_id="group", text=text)
    else:
        post.assert_not_awaited()


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_timestamp_sentinel_is_preserved(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    adapter = install_api(
        monkeypatch,
        provider,
        [
            response_payload(provider, [text_output(provider, '{"iso":"FAILED"}')]),
        ],
        [],
        model=AIModel.POWERFUL,
    )
    monkeypatch.setattr(client, "AI_PROVIDER", provider)
    monkeypatch.setattr(client, "AnthropicProvider", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(client, "OpenAIProvider", lambda *_args, **_kwargs: adapter)
    assert asyncio.run(AIClient(AIModel.POWERFUL).resolve_timestamp("nonsense")) == "FAILED"


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_reminder_creation_is_unavailable_without_trigger_context(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    requests: list[dict[str, object]] = []
    adapter = install_api(
        monkeypatch,
        provider,
        [
            response_payload(
                provider,
                [
                    tool_call(
                        provider,
                        "create_reminder",
                        {
                            "time": "tomorrow",
                            "message": "buy milk",
                        },
                        "call_reminder",
                    )
                ],
                status="tools",
            ),
            response_payload(provider, [text_output(provider, "No reminder context.")]),
        ],
        requests,
    )
    monkeypatch.setattr(client, "AI_PROVIDER", provider)
    monkeypatch.setattr(client, "AnthropicProvider", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(client, "OpenAIProvider", lambda *_args, **_kwargs: adapter)
    reminder = AsyncMock()
    monkeypatch.setattr(client, "execute_create_reminder", reminder)
    asyncio.run(AIClient().generate_response([], allow_webfetch=False, allow_db_query=False))
    reminder.assert_not_awaited()
    assert requests[0]["tools"] == []
