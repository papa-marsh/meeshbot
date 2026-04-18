from datetime import UTC, datetime
from typing import cast

from meeshbot.config import GROUPME_TOKEN
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.queries import get_bot_id, upsert_message, upsert_user
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models import GroupMeGroup


async def sync(webhook: GroupMeWebhookPayload) -> None:
    if webhook.text is None:
        return

    args = webhook.text.split()
    if len(args) < 2:
        await GroupMeClient().post_message(
            group_id=webhook.group_id,
            text="Usage: /sync <groups|messages>",
        )
        return

    match args[1].lower():
        case "groups":
            await sync_groups(webhook)
        case "messages":
            await sync_messages(webhook, args[2:])
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


async def sync_messages(webhook: GroupMeWebhookPayload, args: list[str]) -> None:
    client = GroupMeClient()

    if not args:
        await client.post_message(
            group_id=webhook.group_id,
            text="Usage: /sync messages <group_id> [before_id]",
        )
        return

    target_group_id = args[0]
    before_id: str | None = args[1] if len(args) > 1 else None

    await client.post_message(
        group_id=webhook.group_id,
        text=f"Starting message sync for group {target_group_id}..."
        + (f" (resuming from {before_id})" if before_id else ""),
    )

    total_synced = 0

    try:
        while True:
            messages = await client.get_messages(
                group_id=target_group_id,
                before_id=before_id,
                limit=100,
            )

            if not messages:
                break

            for message in messages:
                await upsert_user(
                    user_id=message.user_id,
                    name=message.name,
                    image_url=message.avatar_url,
                )
                await upsert_message(group_id=target_group_id, message=message)

            total_synced += len(messages)
            before_id = messages[-1].id

            if total_synced % 500 == 0:
                resume_cmd = f"/sync messages {target_group_id} {before_id}"
                await client.post_message(
                    group_id=webhook.group_id,
                    text=f"Synced {total_synced} messages... (resume: {resume_cmd})",
                )

    except Exception as e:
        error_text = str(e).replace(GROUPME_TOKEN, "<token>")
        resume_hint = (
            f"\n\nResume with: /sync messages {target_group_id} {before_id}" if before_id else ""
        )
        await client.post_message(
            group_id=webhook.group_id,
            text=f"Sync failed after {total_synced} messages: {error_text}{resume_hint}",
        )
        return

    await client.post_message(
        group_id=webhook.group_id,
        text=f"Sync complete. {total_synced} messages synced for group {target_group_id}.",
    )
