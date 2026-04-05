from datetime import UTC, datetime
from typing import cast

from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.secrets import BOTS_BY_GROUP
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models import GroupMeBot, GroupMeGroup


async def sync(webhook: GroupMeWebhookPayload) -> None:
    if webhook.text is None:
        return

    args = webhook.text.split()
    if len(args) < 2:
        await GroupMeClient().post_message(
            group_id=webhook.group_id,
            text="Usage: /sync <target>",
        )
        return

    match args[1].lower():
        case "groups":
            await sync_groups(webhook)
        case unknown:
            await GroupMeClient().post_message(
                group_id=webhook.group_id,
                text=f"Unknown sync target: {unknown}",
            )


async def sync_groups(webhook: GroupMeWebhookPayload) -> None:
    client = GroupMeClient()
    groups = await client.get_groups()
    group_count = 0
    bot_count = 0

    for group in groups:
        created_at = datetime.fromtimestamp(group.created_at, tz=UTC)

        group_obj, created = await GroupMeGroup.objects.get_or_create(
            id=group.id,
            defaults={
                "name": group.name,
                "image_url": group.image_url,
                "created_at": created_at,
            },
        )
        group_obj = cast(GroupMeGroup, group_obj)

        if not created:
            group_obj.name = group.name
            group_obj.image_url = group.image_url
            await group_obj.save()

        group_count += 1

        bot_id = BOTS_BY_GROUP.get(group.id)
        if bot_id is None:
            continue

        bot_obj, created = await GroupMeBot.objects.get_or_create(
            id=bot_id,
            defaults={"group_id": group.id},
        )
        bot_obj = cast(GroupMeBot, bot_obj)

        if not created:
            bot_obj.group = group_obj
            await bot_obj.save()

        bot_count += 1

    await client.post_message(
        group_id=webhook.group_id,
        text=f"Synced {group_count} groups and {bot_count} bots.",
    )
