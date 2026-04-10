from datetime import UTC, datetime
from typing import cast

from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.queries import get_bot_id
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models import GroupMeGroup


async def sync(webhook: GroupMeWebhookPayload) -> None:
    if webhook.text is None:
        return

    args = webhook.text.split()
    if len(args) < 2:
        await GroupMeClient().post_message(
            group_id=webhook.group_id,
            text="Usage: /sync <groups>",
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
    botless_groups = set()

    for group in groups:
        if get_bot_id(group.id) is None:
            botless_groups.add(group.name)

        group_obj, created = await GroupMeGroup.objects.get_or_create(
            id=group.id,
            defaults={
                "name": group.name,
                "image_url": group.image_url,
                "created_at": datetime.fromtimestamp(group.created_at, tz=UTC),
            },
        )
        group_obj = cast(GroupMeGroup, group_obj)

        if not created:
            group_obj.name = group.name
            group_obj.image_url = group.image_url
            await group_obj.save()

        group_count += 1

    text = f"Synced {group_count} groups."
    if botless_groups:
        text += "\n\nGroups missing bots:"
        for botless_group in botless_groups:
            text += f"\n{botless_group}"

    await client.post_message(group_id=webhook.group_id, text=text)
