import asyncio
from datetime import UTC, datetime
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from meeshbot.commands import volume as volume_command
from meeshbot.commands.sync import sync_groups
from meeshbot.handlers import groupme
from meeshbot.integrations.ai import client
from meeshbot.integrations.ai.client import AIClient
from meeshbot.integrations.ai.types import Context
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models import GroupMeGroup
from meeshbot.utils import volume
from tests.test_ai_providers import install_api, response_payload, text_output, tool_call


@pytest.fixture
def groups(monkeypatch: pytest.MonkeyPatch) -> dict[str, GroupMeGroup]:
    rows = {
        id: GroupMeGroup(id=id, name=id, created_at=datetime(2026, 9, 18, tzinfo=UTC))
        for id in ("group", "other")
    }

    async def get(*, id: str) -> GroupMeGroup:
        return rows[id].model_copy(deep=True)

    async def save(self: GroupMeGroup, *, update_fields: set[str] | None = None) -> None:
        for name in update_fields if update_fields is not None else GroupMeGroup.model_fields:
            setattr(rows[self.id], name, getattr(self, name))

    monkeypatch.setattr(GroupMeGroup, "save", save)
    monkeypatch.setattr(volume, "GroupMeGroup", SimpleNamespace(objects=SimpleNamespace(get=get)))
    return rows


@pytest.mark.parametrize(
    "value, expected", [("7", 30), ("1.5", 85), ("1", 90), ("10", 0), ("1.75", 82.5)]
)
def test_volume_command_persists_threshold_only_for_its_group(
    monkeypatch: pytest.MonkeyPatch, groups: dict[str, GroupMeGroup], value: str, expected: float
) -> None:
    post = AsyncMock()
    monkeypatch.setattr(GroupMeClient, "post_message", post)
    asyncio.run(
        volume_command(
            GroupMeWebhookPayload.model_construct(group_id="group", text=f"/volume {value}")
        )
    )
    assert groups["group"].response_threshold == expected
    assert groups["other"].response_threshold == 50
    assert f"{value}/10" in post.call_args.kwargs["text"]
    post.reset_mock()
    asyncio.run(
        volume_command(GroupMeWebhookPayload.model_construct(group_id="group", text="/volume"))
    )
    assert f"{value}/10" in post.call_args.kwargs["text"]


def test_volume_defaults_to_five(
    monkeypatch: pytest.MonkeyPatch, groups: dict[str, GroupMeGroup]
) -> None:
    post = AsyncMock()
    monkeypatch.setattr(GroupMeClient, "post_message", post)
    asyncio.run(
        volume_command(GroupMeWebhookPayload.model_construct(group_id="group", text="/volume"))
    )
    assert "5/10" in post.call_args.kwargs["text"]


@pytest.mark.parametrize(
    "value", ["0", "10.1", "-1", "NaN", "inf", "-inf", "1e999", "nope", "7 extra"]
)
def test_invalid_command_preserves_volume(
    monkeypatch: pytest.MonkeyPatch, groups: dict[str, GroupMeGroup], value: str
) -> None:
    groups["group"].response_threshold = 85
    post = AsyncMock()
    monkeypatch.setattr(GroupMeClient, "post_message", post)
    asyncio.run(
        volume_command(
            GroupMeWebhookPayload.model_construct(group_id="group", text=f"/volume {value}")
        )
    )
    assert groups["group"].response_threshold == 85
    assert "set to" not in post.call_args.kwargs["text"]


@pytest.mark.parametrize("text", ["/volume 7", "/ping", "/unknown", "/", "/timeout done"])
def test_slash_commands_dispatch_and_persist_without_ai_evaluation(
    monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    persist, post, paused, evaluate, respond = (AsyncMock() for _ in range(5))
    monkeypatch.setattr(groupme, "sync_message_to_db", persist)
    monkeypatch.setattr(GroupMeClient, "post_message", post)
    monkeypatch.setattr(groupme, "flag_enabled", paused)
    monkeypatch.setattr(groupme, "should_respond", evaluate)
    monkeypatch.setattr(groupme, "send_ai_response", respond)
    monkeypatch.setattr(
        import_module("meeshbot.commands.volume"), "set_volume", AsyncMock(return_value=7)
    )
    monkeypatch.setattr(import_module("meeshbot.commands.timeout"), "disable_flag", AsyncMock())
    webhook = GroupMeWebhookPayload.model_construct(text=text, group_id="group", name="Marshall")
    asyncio.run(groupme.handle_groupme_webhook(webhook))
    persist.assert_awaited_once_with(webhook)
    post.assert_awaited_once()
    paused.assert_not_awaited()
    evaluate.assert_not_awaited()
    respond.assert_not_awaited()


def test_ordinary_messages_still_reach_ai_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(groupme, "sync_message_to_db", AsyncMock())
    monkeypatch.setattr(groupme, "flag_enabled", AsyncMock(return_value=False))
    evaluate = AsyncMock(return_value=True)
    respond = AsyncMock()
    monkeypatch.setattr(groupme, "should_respond", evaluate)
    monkeypatch.setattr(groupme, "send_ai_response", respond)
    webhook = GroupMeWebhookPayload.model_construct(text="hello", group_id="group", name="Marshall")
    asyncio.run(groupme.handle_groupme_webhook(webhook))
    evaluate.assert_awaited_once_with("group")
    respond.assert_awaited_once_with("group", trigger=webhook)


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
@pytest.mark.parametrize("level, expected", [("1.5", 85), ("NaN", 50), ("11", 50), (7, 50)])
def test_volume_tool_uses_trusted_group_and_validates_before_persisting(
    monkeypatch: pytest.MonkeyPatch,
    groups: dict[str, GroupMeGroup],
    provider: str,
    level: object,
    expected: float,
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
                        provider, "set_volume", {"level": level, "group_id": "other"}, "volume_call"
                    )
                ],
                status="tools",
            ),
            response_payload(provider, [text_output(provider, "Done.")]),
        ],
        requests,
    )
    monkeypatch.setattr(client, "AI_PROVIDER", provider)
    monkeypatch.setattr(client, "AnthropicProvider", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(client, "OpenAIProvider", lambda *_args, **_kwargs: adapter)
    asyncio.run(
        AIClient().generate_response(
            [],
            context=Context("group"),
            system_prompt="Test system prompt",
            allow_webfetch=False,
            allow_db_query=False,
        )
    )
    assert groups["group"].response_threshold == expected
    assert groups["other"].response_threshold == 50
    assert [tool["name"] for tool in requests[0]["tools"]] == ["set_volume"]
    assert (
        requests[0]["system" if provider == "anthropic" else "instructions"] == "Test system prompt"
    )
    continuation = str(requests[1])
    assert ("Volume set to 1.5/10" if expected == 85 else "Error:") in continuation


def test_group_sync_preserves_concurrent_volume_change(
    monkeypatch: pytest.MonkeyPatch, groups: dict[str, GroupMeGroup]
) -> None:
    stale = groups["group"].model_copy(deep=True)
    asyncio.run(volume.set_volume("group", "1.5"))
    monkeypatch.setattr(
        import_module("meeshbot.commands.sync"),
        "GroupMeGroup",
        SimpleNamespace(
            objects=SimpleNamespace(get_or_create=AsyncMock(return_value=(stale, False)))
        ),
    )
    monkeypatch.setattr(
        GroupMeClient,
        "get_groups",
        AsyncMock(
            return_value=[
                SimpleNamespace(id="group", name="New name", image_url=None, created_at=0)
            ]
        ),
    )
    monkeypatch.setattr(GroupMeClient, "post_message", AsyncMock())
    asyncio.run(sync_groups(GroupMeWebhookPayload.model_construct(group_id="group")))
    assert groups["group"].name == "New name"
    assert groups["group"].response_threshold == 85
