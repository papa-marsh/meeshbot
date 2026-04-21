"""Reminder dispatcher — called by the scheduler to send due reminders."""

from datetime import UTC, datetime

from structlog.stdlib import get_logger

from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import (
    MentionsAttachment,
    MessageAttachment,
    ReplyAttachment,
)
from meeshbot.models import Reminder
from meeshbot.models.group import GroupMeGroup
from meeshbot.models.user import GroupMeUser

log = get_logger()

_MENTION_PREFIX = "🔔 Reminder for "


async def send_due_reminders() -> None:
    """Fetch all unsent reminders whose ETA has passed and dispatch them."""
    now = datetime.now(tz=UTC)

    due: list[Reminder] = (
        await Reminder.objects.filter(
            sent=False,
            eta__lte=now,
        )
        .join("group", "sender")
        .order_by("eta")
        .all()
    )

    if not due:
        return

    log.info("Dispatching due reminders", count=len(due))

    for reminder in due:
        await _send_reminder(reminder)


async def _send_reminder(reminder: Reminder) -> None:
    if not (isinstance(reminder.group, GroupMeGroup) and isinstance(reminder.sender, GroupMeUser)):
        raise TypeError("Reminder model must be joined by `group` and `sender`")

    first_name = reminder.sender.name.split()[0]
    text = f"{_MENTION_PREFIX}{first_name}: {reminder.message}"

    prefix_bytes = len(_MENTION_PREFIX.encode("utf-8"))
    name_bytes = len(first_name.encode("utf-8"))

    attachments: list[MessageAttachment] = [
        ReplyAttachment(
            type="reply",
            reply_id=reminder.command_message_id,
            base_reply_id=reminder.command_message_id,
        ),
        MentionsAttachment(
            type="mentions",
            user_ids=[reminder.sender.id],
            loci=[(prefix_bytes, name_bytes)],
        ),
    ]

    await GroupMeClient().post_message(
        group_id=reminder.group.id,
        text=text,
        attachments=attachments,
    )

    reminder.sent = True
    await reminder.save()

    log.info(
        "Reminder sent",
        reminder_id=reminder.id,
        group_id=reminder.group.id,
        sender_id=reminder.sender.id,
    )
