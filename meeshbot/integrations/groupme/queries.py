"""Database utilities for GroupMe integration."""

from datetime import UTC, datetime

from meeshbot.integrations.groupme.secrets import BOTS_BY_GROUP
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models import GroupMeGroup, GroupMeMessage, GroupMeUser


def get_bot_id(group_id: str, raise_if_missing: bool = False) -> str | None:
    bot_id = BOTS_BY_GROUP.get(group_id)

    if bot_id is None and raise_if_missing:
        raise ValueError(f"Bot ID lookup failed for group ID {group_id}")

    return bot_id


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
