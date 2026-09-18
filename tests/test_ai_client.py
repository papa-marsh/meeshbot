import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from meeshbot.config import TIMEZONE
from meeshbot.integrations.ai import chat, client
from meeshbot.integrations.ai.client import AIClient, ResponseLikelihood
from meeshbot.integrations.ai.context import IMAGE_ANALYSIS_CONTEXT, SEND_AI_RESPONSE_CONTEXT
from meeshbot.integrations.ai.provider import AIProvider, execute_tool
from meeshbot.integrations.ai.providers.anthropic import AnthropicProvider
from meeshbot.integrations.ai.providers.openai import OpenAIProvider
from meeshbot.integrations.ai.tools import DB_QUERY_TOOL
from meeshbot.integrations.ai.types import AIMessage, AIModel, AITool, Context
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
    identity = Context("real-group", "real-sender", "real-message")
    result = asyncio.run(
        AIClient().generate_response(
            [],
            allow_webfetch=False,
            allow_db_query=False,
            context=identity,
        )
    )
    assert result == "Reminder created."
    reminder.assert_awaited_once_with(identity, "tomorrow", "buy milk")
    database.assert_not_awaited()
    tool_names = {tool["name"] for tool in requests[0]["tools"]}
    assert "create_reminder" in tool_names
    assert "query_database" not in tool_names


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


@pytest.mark.parametrize(
    "threshold, score, expected",
    [
        (50, 49, False),
        (50, 50, True),
        (30, 30, True),
        (85, 84, False),
        (85, 85, True),
        (0, 0, True),
        (90, 89, False),
        (90, 90, True),
        (82.5, 82, False),
        (82.5, 83, True),
    ],
)
def test_classifier_sees_transcript_as_evidence_and_applies_threshold(
    monkeypatch: pytest.MonkeyPatch, threshold: float, score: int, expected: bool
) -> None:
    history: list[AIMessage] = [
        {"role": "assistant", "content": "MeeshBot: hi"},
        {"role": "user", "content": "Marshall: question"},
    ]
    monkeypatch.setattr(chat, "build_message_history", AsyncMock(return_value=history))
    get_threshold = AsyncMock(return_value=threshold)
    monkeypatch.setattr(chat, "get_response_threshold", get_threshold)
    score_call = AsyncMock(return_value=ResponseLikelihood(reason="Addressed", score=score))
    monkeypatch.setattr(client.AIClient, "score_response_likelihood", score_call)
    monkeypatch.setattr(client, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(client, "ANTHROPIC_API_KEY", "test")
    assert asyncio.run(chat.should_respond("group")) is expected
    get_threshold.assert_awaited_once_with("group")
    prompt = score_call.call_args.kwargs["history_text"]
    assert prompt.startswith("MeeshBot: hi")
    assert prompt.endswith("--- The message you are evaluating is: ---\n\nMarshall: question")


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("text", ["", "hello"])
@pytest.mark.parametrize("with_trigger", [False, True])
def test_chat_controls_database_access_and_skips_empty_posts(
    monkeypatch: pytest.MonkeyPatch, public: bool, text: str, with_trigger: bool
) -> None:
    monkeypatch.setattr(chat, "build_message_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat, "get_volume", AsyncMock(return_value=1.5))
    monkeypatch.setattr(chat, "is_public_group", lambda _group: public)
    monkeypatch.setattr(client, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(client, "ANTHROPIC_API_KEY", "test")
    generate = AsyncMock(return_value=text)
    post = AsyncMock()
    monkeypatch.setattr(client.AIClient, "generate_response", generate)
    monkeypatch.setattr(chat.GroupMeClient, "post_message", post)
    trigger = (
        GroupMeWebhookPayload.model_construct(id="msg", user_id="sender", group_id="group")
        if with_trigger
        else None
    )
    asyncio.run(chat.send_ai_response("group", trigger=trigger))
    assert generate.call_args.kwargs["allow_db_query"] is not public
    assert generate.call_args.kwargs["context"] == (
        Context("group", "sender", "msg") if with_trigger else Context("group")
    )
    assert generate.call_args.kwargs["system_prompt"] == SEND_AI_RESPONSE_CONTEXT
    assert "current volume is: 1.5/10" in generate.call_args.kwargs["messages"][-1]["content"]
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
@pytest.mark.parametrize(
    "context",
    [
        Context("group"),
        Context("group", sender_id="sender"),
        Context("group", trigger_message_id="msg"),
    ],
)
def test_reminder_creation_is_unavailable_without_trigger_context(
    monkeypatch: pytest.MonkeyPatch, provider: str, context: Context
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
    asyncio.run(
        AIClient().generate_response(
            [], context=context, allow_webfetch=False, allow_db_query=False
        )
    )
    reminder.assert_not_awaited()
    assert "create_reminder" not in {tool["name"] for tool in requests[0]["tools"]}
    assert "set_volume" in {tool["name"] for tool in requests[0]["tools"]}


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_image_description_sends_native_image_input_to_selected_provider(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    requests: list[dict[str, object]] = []
    adapter = install_api(
        monkeypatch,
        provider,
        [response_payload(provider, [text_output(provider, '{"description":" A dog. "}')])],
        requests,
        model=AIModel.CHEAP,
    )
    monkeypatch.setattr(client, "AI_PROVIDER", provider)
    monkeypatch.setattr(client, "AnthropicProvider", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(client, "OpenAIProvider", lambda *_args, **_kwargs: adapter)
    url = "https://i.groupme.com/example.png"
    assert asyncio.run(AIClient(AIModel.CHEAP).describe_image(url)) == "A dog."
    request = requests[0]
    assert not request.get("tools")
    if provider == "anthropic":
        assert request["model"] == "claude-haiku-4-5"
        assert request["system"] == IMAGE_ANALYSIS_CONTEXT
        assert request["messages"][0]["content"][0] == {
            "type": "image",
            "source": {"type": "url", "url": url},
        }
    else:
        assert request["model"] == "gpt-5.6-luna"
        assert request["instructions"] == IMAGE_ANALYSIS_CONTEXT
        assert request["input"][0]["content"][0] == {
            "type": "input_image",
            "image_url": url,
            "detail": "auto",
        }
        assert request["store"] is False


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_empty_image_description_is_not_a_success(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    adapter = install_api(
        monkeypatch,
        provider,
        [response_payload(provider, [text_output(provider, '{"description":" "}')])],
        [],
        model=AIModel.CHEAP,
    )
    monkeypatch.setattr(client, "AI_PROVIDER", provider)
    monkeypatch.setattr(client, "AnthropicProvider", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(client, "OpenAIProvider", lambda *_args, **_kwargs: adapter)
    with pytest.raises(ValueError):
        asyncio.run(AIClient(AIModel.CHEAP).describe_image("https://i.groupme.com/example.png"))


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://example.com/image",
        "https:///missing",
        "https://user:password@example.com/image",
    ],
)
def test_invalid_image_urls_are_not_sent_to_provider(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setattr(client, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(client, "ANTHROPIC_API_KEY", "test")
    generate = AsyncMock()
    monkeypatch.setattr(AnthropicProvider, "generate_structured", generate)
    with pytest.raises(ValueError):
        asyncio.run(AIClient().describe_image(url))
    generate.assert_not_awaited()
