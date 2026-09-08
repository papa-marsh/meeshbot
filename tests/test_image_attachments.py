import asyncio
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from meeshbot.integrations.ai import chat, client
from meeshbot.integrations.ai.client import AIClient
from meeshbot.integrations.groupme import image_analysis, queries
from meeshbot.integrations.groupme.attachments import (
    image_analysis_due,
    merge_attachments,
    render_attachments,
    serialize_attachments,
)
from meeshbot.integrations.groupme.types import (
    GroupMeWebhookPayload,
    ImageAnalysisStatus,
    ImageAttachment,
    ImageMetadata,
    Message,
)

NOW = datetime(2026, 9, 7, 12, tzinfo=UTC)
IMAGE_URL = "https://i.groupme.com/example.png"


@pytest.mark.parametrize(
    "metadata, expected",
    [
        (None, True),
        ({}, True),
        ({"status": "complete"}, False),
        ({"status": "failed", "updated": NOW.isoformat()}, True),
        ({"status": "in_progress", "updated": NOW.isoformat()}, False),
        ({"status": "in_progress", "updated": (NOW - timedelta(seconds=299)).isoformat()}, False),
        ({"status": "in_progress", "updated": (NOW - timedelta(minutes=5)).isoformat()}, True),
        ({"status": "in_progress", "updated": "2026-09-07T06:55:00-05:00"}, True),
        ({"status": "in_progress"}, True),
        ({"status": "in_progress", "updated": "bad timestamp"}, True),
        ({"status": "in_progress", "updated": "2026-09-07T12:00:00"}, True),
        ({"status": "in_progress", "updated": 123}, True),
    ],
)
def test_analysis_eligibility_uses_status_update_time(metadata: object, expected: bool) -> None:
    assert image_analysis_due(metadata, NOW) is expected


def test_image_metadata_round_trips_through_groupme_types_but_is_not_trusted_on_ingest() -> None:
    metadata = ImageMetadata(status=ImageAnalysisStatus.COMPLETE, updated=NOW, description="A dog.")
    image = ImageAttachment(type="image", url=IMAGE_URL, metadata=metadata)
    payload = Message.model_validate(
        {
            "id": "msg",
            "source_guid": "guid",
            "created_at": 1,
            "user_id": "sender",
            "group_id": "group",
            "name": "Marshall",
            "system": False,
            "attachments": [image.model_dump(mode="json")],
        }
    )
    assert isinstance(payload.attachments[0], ImageAttachment)
    assert payload.attachments[0].metadata == metadata
    assert "metadata" not in serialize_attachments(payload.attachments)[0]


def test_sync_merges_metadata_by_image_url_without_resurrecting_removed_attachments() -> None:
    metadata = {"status": "complete", "description": "A dog.", "updated": NOW.isoformat()}
    stored = [
        {"type": "image", "url": IMAGE_URL, "metadata": metadata, "blur_hash": "old"},
        {"type": "image", "url": "https://i.groupme.com/removed.png", "metadata": metadata},
    ]
    incoming = [
        {"type": "video", "url": IMAGE_URL},
        {"type": "image", "url": "https://i.groupme.com/new.png"},
        {"type": "image", "url": IMAGE_URL, "blur_hash": "new"},
    ]
    result = merge_attachments(incoming, stored)
    assert result == [incoming[0], incoming[1], {**incoming[2], "metadata": metadata}]
    assert "metadata" not in incoming[2]
    assert stored[0]["blur_hash"] == "old"


def test_history_renders_content_and_states_but_not_structural_attachments() -> None:
    attachments = [
        {"type": "image", "metadata": {"status": "complete", "description": "A dog."}},
        {"type": "image", "metadata": {"status": "in_progress"}},
        {"type": "image", "metadata": {"status": "failed"}},
        {"type": "image"},
        {"type": "video"},
        {"type": "file"},
        {"type": "mentions", "user_ids": ["sender"]},
        {"type": "reply", "reply_id": "previous"},
    ]
    entry = AIClient.build_message_history_entry("Marshall", NOW, "Look at this", attachments)
    assert entry["role"] == "user"
    assert entry["content"].endswith(
        "Look at this\n"
        "[Image: A dog.]\n"
        "[Image: Analysis in progress]\n"
        "[Image: Image analysis failed]\n"
        "[Image: Not analyzed]\n"
        "[Video: Unable to analyze video attachments]\n"
        "[File: Unable to analyze file attachments]"
    )
    assert render_attachments([]) == ""


def test_database_history_includes_attachment_only_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        chat,
        "get_message_history",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    sender_id="sender",
                    timestamp=NOW,
                    text=None,
                    attachments=[
                        {
                            "type": "image",
                            "metadata": {"status": "complete", "description": "A dog."},
                        }
                    ],
                )
            ]
        ),
    )
    monkeypatch.setattr(
        chat,
        "GroupMeUser",
        SimpleNamespace(
            objects=SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(name="Marshall")))
        ),
    )
    history = asyncio.run(chat.build_message_history("group"))
    assert len(history) == 1
    assert history[0]["content"].endswith(": [Image: A dog.]")


@dataclass
class MessageStore:
    rows: dict[str, SimpleNamespace] = field(default_factory=dict)
    before_update: Callable[[], None] | None = None

    async def get_or_none(self, *, id: str) -> SimpleNamespace | None:
        return deepcopy(self.rows.get(id))

    async def get_or_create(
        self, *, id: str, defaults: dict[str, object]
    ) -> tuple[SimpleNamespace, bool]:
        created = id not in self.rows
        if created:
            self.rows[id] = SimpleNamespace(id=id, **deepcopy(defaults))
        return deepcopy(self.rows[id]), created

    def filter(self, **filters: object) -> MessageQuery:
        return MessageQuery(self, filters)


@dataclass
class MessageQuery:
    store: MessageStore
    filters: dict[str, object]

    async def update(self, **values: object) -> int:
        if self.store.before_update is not None:
            callback, self.store.before_update = self.store.before_update, None
            callback()
        for row in self.store.rows.values():
            if all(getattr(row, key) == value for key, value in self.filters.items()):
                vars(row).update(deepcopy(values))
                return 1
        return 0


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> MessageStore:
    database = MessageStore()
    model = SimpleNamespace(objects=database)
    monkeypatch.setattr(image_analysis, "GroupMeMessage", model)
    monkeypatch.setattr(queries, "GroupMeMessage", model)
    for name in ("GroupMeGroup", "GroupMeUser"):
        monkeypatch.setattr(
            queries, name, SimpleNamespace(objects=SimpleNamespace(get_or_create=AsyncMock()))
        )
    monkeypatch.setattr(image_analysis, "_analysis_slots", asyncio.Semaphore(4))
    monkeypatch.setattr(client, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(client, "ANTHROPIC_API_KEY", "test")
    return database


def api_message() -> Message:
    return Message(
        id="msg",
        source_guid="guid",
        created_at=1,
        user_id="sender",
        group_id="group",
        name="Marshall",
        text="Original text",
        system=False,
        attachments=[ImageAttachment(type="image", url=IMAGE_URL)],
    )


async def wait_for_status(store: MessageStore, status: str, index: int = 0) -> None:
    async with asyncio.timeout(2):
        while store.rows["msg"].attachments[index].get("metadata", {}).get("status") != status:
            await asyncio.sleep(0)
        await asyncio.sleep(0)


@pytest.mark.parametrize("path", ["webhook", "api"])
def test_sync_is_nonblocking_and_preserves_completed_analysis(
    monkeypatch: pytest.MonkeyPatch, store: MessageStore, path: str
) -> None:
    async def scenario() -> None:
        release = asyncio.Event()

        async def describe(_url: str) -> str:
            await release.wait()
            return "A dog."

        analysis = AsyncMock(side_effect=describe)
        monkeypatch.setattr(AIClient, "describe_image", analysis)
        message = api_message()

        async def sync() -> None:
            if path == "api":
                await queries.upsert_message("group", message)
            else:
                webhook = GroupMeWebhookPayload.model_validate(
                    {**message.model_dump(), "sender_id": "sender", "sender_type": "user"}
                )
                await queries.sync_message_to_db(webhook)

        await asyncio.wait_for(sync(), timeout=1)
        started = deepcopy(store.rows["msg"].attachments[0]["metadata"])
        assert started["status"] == "in_progress"
        assert datetime.fromisoformat(started["updated"]).utcoffset() == timedelta(0)
        assert not release.is_set()
        await sync()
        assert store.rows["msg"].attachments[0]["metadata"] == started
        release.set()
        await wait_for_status(store, "complete")
        completed = deepcopy(store.rows["msg"].attachments[0]["metadata"])
        assert completed["description"] == "A dog."
        assert datetime.fromisoformat(completed["updated"]) >= datetime.fromisoformat(
            started["updated"]
        )
        await sync()
        assert store.rows["msg"].attachments[0]["metadata"] == completed
        analysis.assert_awaited_once_with(IMAGE_URL)

    asyncio.run(scenario())


def test_failed_analysis_is_saved_and_retried_on_next_sync(
    monkeypatch: pytest.MonkeyPatch, store: MessageStore
) -> None:
    async def scenario() -> None:
        analysis = AsyncMock(side_effect=[ValueError("Image unavailable"), "A dog."])
        monkeypatch.setattr(AIClient, "describe_image", analysis)
        await queries.upsert_message("group", api_message())
        await wait_for_status(store, "failed")
        assert "description" not in store.rows["msg"].attachments[0]["metadata"]
        await queries.upsert_message("group", api_message())
        await wait_for_status(store, "complete")
        assert analysis.await_count == 2

    asyncio.run(scenario())


def test_analysis_timeout_is_persisted_as_failure(
    monkeypatch: pytest.MonkeyPatch, store: MessageStore
) -> None:
    async def scenario() -> None:
        async def describe(_url: str) -> str:
            await asyncio.Event().wait()
            return "unreachable"

        monkeypatch.setattr(AIClient, "describe_image", AsyncMock(side_effect=describe))
        monkeypatch.setattr(image_analysis, "ANALYSIS_TIMEOUT_SECONDS", 0)
        await queries.upsert_message("group", api_message())
        await wait_for_status(store, "failed")

    asyncio.run(scenario())


@pytest.mark.parametrize("stale", [False, True])
def test_resync_retries_only_stale_in_progress_analysis(
    monkeypatch: pytest.MonkeyPatch, store: MessageStore, stale: bool
) -> None:
    async def scenario() -> None:
        updated = datetime.now(UTC) - timedelta(minutes=6 if stale else 0)
        metadata = {"status": "in_progress", "updated": updated.isoformat()}
        store.rows["msg"] = SimpleNamespace(
            id="msg", attachments=[{"type": "image", "url": IMAGE_URL, "metadata": metadata}]
        )
        analysis = AsyncMock(return_value="A dog.")
        monkeypatch.setattr(AIClient, "describe_image", analysis)
        await queries.upsert_message("group", api_message())
        if stale:
            await wait_for_status(store, "complete")
            analysis.assert_awaited_once_with(IMAGE_URL)
        else:
            assert store.rows["msg"].attachments[0]["metadata"] == metadata
            analysis.assert_not_awaited()

    asyncio.run(scenario())


def test_sync_preserves_analysis_that_finishes_during_its_update(
    monkeypatch: pytest.MonkeyPatch, store: MessageStore
) -> None:
    async def scenario() -> None:
        message = api_message()
        metadata = {"status": "complete", "updated": NOW.isoformat(), "description": "A dog."}
        store.rows["msg"] = SimpleNamespace(
            id="msg", text="Old text", attachments=[{"type": "image", "url": IMAGE_URL}]
        )

        def finish_analysis() -> None:
            store.rows["msg"].attachments[0]["metadata"] = metadata

        store.before_update = finish_analysis
        analysis = AsyncMock()
        monkeypatch.setattr(AIClient, "describe_image", analysis)
        await queries.upsert_message("group", message)
        assert store.rows["msg"].text == message.text
        assert store.rows["msg"].attachments[0]["metadata"] == metadata
        analysis.assert_not_awaited()

    asyncio.run(scenario())


def test_completion_preserves_other_images_and_newer_message_fields(store: MessageStore) -> None:
    async def scenario() -> None:
        started = ImageMetadata(status=ImageAnalysisStatus.IN_PROGRESS, updated=NOW)
        result = ImageMetadata(
            status=ImageAnalysisStatus.COMPLETE, updated=NOW, description="A dog."
        )
        store.rows["msg"] = SimpleNamespace(
            id="msg",
            text="Updated text",
            attachments=[
                {"type": "video", "url": IMAGE_URL},
                {
                    "type": "image",
                    "url": IMAGE_URL,
                    "metadata": started.model_dump(mode="json", exclude_none=True),
                },
                {"type": "image", "url": "https://i.groupme.com/other.png"},
            ],
        )
        other_metadata = {"status": "complete", "description": "A cat.", "updated": NOW.isoformat()}

        def finish_other_image() -> None:
            store.rows["msg"].attachments[2]["metadata"] = other_metadata

        store.before_update = finish_other_image
        await image_analysis._save_image_metadata("msg", IMAGE_URL, started, result)
        row = store.rows["msg"]
        assert row.text == "Updated text"
        assert "metadata" not in row.attachments[0]
        assert row.attachments[1]["metadata"]["description"] == "A dog."
        assert row.attachments[2]["metadata"] == other_metadata

    asyncio.run(scenario())


@pytest.mark.parametrize("removed", [False, True])
def test_old_analysis_cannot_overwrite_a_retry_or_restore_a_removed_image(
    store: MessageStore, removed: bool
) -> None:
    async def scenario() -> None:
        started = ImageMetadata(status=ImageAnalysisStatus.IN_PROGRESS, updated=NOW)
        retried = ImageMetadata(
            status=ImageAnalysisStatus.IN_PROGRESS, updated=NOW + timedelta(minutes=5)
        )
        result = ImageMetadata(
            status=ImageAnalysisStatus.COMPLETE, updated=NOW, description="Old result"
        )
        attachments = (
            []
            if removed
            else [
                {
                    "type": "image",
                    "url": IMAGE_URL,
                    "metadata": retried.model_dump(mode="json", exclude_none=True),
                }
            ]
        )
        store.rows["msg"] = SimpleNamespace(id="msg", attachments=deepcopy(attachments))
        await image_analysis._save_image_metadata("msg", IMAGE_URL, started, result)
        assert store.rows["msg"].attachments == attachments

    asyncio.run(scenario())
