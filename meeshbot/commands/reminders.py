import uuid
from datetime import datetime
from typing import cast

from meeshbot.config import TIMEZONE
from meeshbot.integrations.anthropic.client import ERROR_OUTPUT, AnthropicClient, ClaudeModel
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.queries import is_public_group
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models import GroupMeUser, Reminder
from meeshbot.models.group import GroupMeGroup
from meeshbot.utils.dates import local_now, verbose_datetime


async def remindme(webhook: GroupMeWebhookPayload) -> None:
    if webhook.text is None:
        return

    body = webhook.text[len("/remindme") :].strip()
    parts = body.split(" - ", maxsplit=1)

    client = GroupMeClient()

    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        await client.post_message(
            group_id=webhook.group_id,
            text="Do it like this IDIOT:\n`/remindme <time> - <message>`",
        )
        return

    time_str, message = parts[0].strip(), parts[1].strip()

    eta_iso = await AnthropicClient(model=ClaudeModel.OPUS).resolve_timestamp(time_str)

    if eta_iso.strip() == ERROR_OUTPUT:
        await client.post_message(
            group_id=webhook.group_id,
            text="I can't figure out when that is... IDIOT",
        )
        return

    eta = datetime.fromisoformat(eta_iso).replace(tzinfo=TIMEZONE)
    now = local_now()

    if eta <= now:
        await client.post_message(
            group_id=webhook.group_id,
            text="I can't remind you of something in the past IDIOT",
        )
        return

    await Reminder.objects.create(
        id=str(uuid.uuid4()),
        group_id=webhook.group_id,
        sender_id=webhook.user_id,
        command_message_id=webhook.id,
        message=message,
        eta=eta,
        created_at=now,
    )

    first_name = webhook.name.split()[0]
    await client.post_message(
        group_id=webhook.group_id,
        text=f"OK {first_name}, I'll remind you on {verbose_datetime(eta)} 👍",
    )


async def reminders(webhook: GroupMeWebhookPayload) -> None:
    public = is_public_group(webhook.group_id)

    filters: dict[str, str | bool] = {"sent": False}
    if public:
        filters["group_id"] = webhook.group_id

    pending = await Reminder.objects.filter(**filters).order_by("eta").all()

    client = GroupMeClient()

    if not pending:
        await client.post_message(
            group_id=webhook.group_id,
            text="Couldn't find any upcoming reminders",
        )
        return

    lines = ["📋 Upcoming Reminders:\n"]
    for reminder in pending:
        user = cast(GroupMeUser, reminder.sender)
        first_name = user.name.split()[0]
        line_text = f'{first_name} - {verbose_datetime(reminder.eta)}\n"{reminder.message}"'
        if not public:
            group = await GroupMeGroup.objects.get(id=reminder.group_id)
            line_text += f"\n({group.name})\n"
        lines.append(line_text)

    await client.post_message(
        group_id=webhook.group_id,
        text="\n".join(lines),
    )
