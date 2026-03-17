"""Database utilities for GroupMe integration."""

from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models import GroupMeBot, GroupMeGroup, GroupMeMessage, GroupMeUser


async def get_bot_id(group_id: str) -> str:
    """Return the bot ID for the given group."""
    bot: GroupMeBot = await GroupMeBot.objects.filter(group_id=group_id).get()
    return bot.id


async def get_group_ids() -> list[str]:
    """Return all configured group IDs."""
    bots = await GroupMeBot.objects.all()
    return [bot.group_id for bot in bots]


async def sync_message_to_db(message: GroupMeWebhookPayload) -> None:
    """Persist a GroupMe message to the database."""
    await GroupMeGroup.objects.get_or_create(
        id=message.group_id,
        defaults={"name": message.group_id, "created_at": message.created_at, "members": {}},
    )

    await GroupMeUser.objects.get_or_create(
        id=message.user_id,
        defaults={"name": message.name, "image_url": message.avatar_url},
    )

    await GroupMeMessage.objects.get_or_create(
        id=message.id,
        defaults={
            "group_id": message.group_id,
            "sender_id": message.user_id,
            "text": message.text,
            "system": message.system,
            "attachments": [a.model_dump() for a in message.attachments],
            "timestamp": message.created_at,
        },
    )
