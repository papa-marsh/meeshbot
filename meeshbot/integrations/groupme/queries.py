"""Database utilities for GroupMe integration."""

from datetime import UTC, datetime
from typing import TypedDict, cast

from oxyde.queries.aggregates import Count

from meeshbot.integrations.groupme.secrets import ADMIN_USER_IDS, BOTS_BY_GROUP, PUBLIC_GROUPS
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload, Message
from meeshbot.models import GroupMeGroup, GroupMeMessage, GroupMeUser


def get_bot_id(group_id: str, raise_if_missing: bool = False) -> str | None:
    bot_id = BOTS_BY_GROUP.get(group_id)

    if bot_id is None and raise_if_missing:
        raise ValueError(f"Bot ID lookup failed for group ID {group_id}")

    return bot_id


def is_admin_user(user_id: str) -> bool:
    return user_id in ADMIN_USER_IDS


def is_public_group(group_id: str) -> bool:
    return group_id in PUBLIC_GROUPS


async def sync_message_to_db(message: GroupMeWebhookPayload) -> None:
    """Persist a GroupMe message to the database."""
    created_at = datetime.fromtimestamp(message.created_at, tz=UTC)

    await GroupMeGroup.objects.get_or_create(
        id=message.group_id,
        defaults={
            "name": message.group_id,
            "created_at": created_at,
        },
    )

    await GroupMeUser.objects.get_or_create(
        id=message.user_id,
        defaults={
            "name": message.name,
            "image_url": message.avatar_url,
        },
    )

    await GroupMeMessage.objects.get_or_create(
        id=message.id,
        defaults={
            "group_id": message.group_id,
            "sender_id": message.user_id,
            "text": message.text,
            "system": message.system,
            "attachments": [a.model_dump() for a in message.attachments],
            "timestamp": created_at,
        },
    )


async def upsert_user(user_id: str, name: str, image_url: str | None) -> None:
    """Create or update a GroupMeUser by ID."""
    obj, created = await GroupMeUser.objects.get_or_create(
        id=user_id,
        defaults={"name": name, "image_url": image_url},
    )
    user = cast(GroupMeUser, obj)
    if not created:
        user.name = name
        user.image_url = image_url
        await user.save()


async def upsert_message(group_id: str, message: Message) -> None:
    """Create or update a GroupMeMessage from a GroupMe API Message object."""
    timestamp = datetime.fromtimestamp(message.created_at, tz=UTC)
    attachments = [a.model_dump() for a in message.attachments]

    existing = await GroupMeMessage.objects.get_or_none(id=message.id)
    if existing is not None:
        existing.text = message.text
        existing.system = message.system
        existing.attachments = attachments
        existing.timestamp = timestamp
        await existing.save()
    else:
        await GroupMeMessage.objects.create(
            id=message.id,
            group_id=group_id,
            sender_id=message.user_id,
            text=message.text,
            system=message.system,
            attachments=attachments,
            timestamp=timestamp,
        )


class _MessageCountRow(TypedDict):
    sender_id: str
    count: int


class MessageCount(TypedDict):
    name: str
    count: int


async def get_message_counts(group_id: str | None = None) -> list[MessageCount]:
    """Return message counts per sender, sorted descending.

    If group_id is provided, counts are scoped to that group.
    Messages with no sender (sender_id is NULL) are excluded.
    """
    filters: dict[str, str | bool] = {"sender_id__isnull": False}
    if group_id is not None:
        filters["group_id"] = group_id

    rows: list[_MessageCountRow] = (
        await GroupMeMessage.objects.filter(**filters)
        .values("sender_id")
        .annotate(count=Count("id"))
        .group_by("sender_id")
        .order_by("-count")
        .all()
    )

    if not rows:
        return []

    sender_ids = [row["sender_id"] for row in rows]
    users = await GroupMeUser.objects.filter(id__in=sender_ids).all()
    name_by_id = {user.id: user.name for user in users}

    return [
        {"name": name_by_id.get(row["sender_id"], row["sender_id"]), "count": row["count"]}
        for row in rows
    ]
