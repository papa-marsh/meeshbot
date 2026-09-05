import uuid
from datetime import datetime

from meeshbot.config import TIMEZONE
from meeshbot.models import Reminder
from meeshbot.utils.dates import local_now


class UnresolvableTimeError(Exception):
    """The natural-language time description could not be resolved to a timestamp."""


class PastTimeError(Exception):
    """The resolved timestamp is not in the future."""


async def create_reminder(
    *,
    group_id: str,
    sender_id: str,
    trigger_message_id: str,
    message: str,
    time_description: str,
) -> datetime:
    """
    Resolve a natural-language time description, validate it, and persist a Reminder.

    Returns the resolved ETA. Raises UnresolvableTimeError or PastTimeError when
    the time description can't produce a valid future timestamp.
    """
    from meeshbot.integrations.ai.client import ERROR_OUTPUT, AIClient
    from meeshbot.integrations.ai.types import AIModel

    eta_iso = await AIClient(model=AIModel.POWERFUL).resolve_timestamp(time_description)

    if eta_iso.strip() == ERROR_OUTPUT:
        raise UnresolvableTimeError(time_description)

    eta = datetime.fromisoformat(eta_iso).replace(tzinfo=TIMEZONE)
    now = local_now()

    if eta <= now:
        raise PastTimeError(eta_iso)

    await Reminder.objects.create(
        id=str(uuid.uuid4()),
        group_id=group_id,
        sender_id=sender_id,
        command_message_id=trigger_message_id,
        message=message,
        eta=eta,
        created_at=now,
    )

    return eta
