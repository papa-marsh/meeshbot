from datetime import datetime

from meeshbot.config import TIMEZONE
from meeshbot.integrations.anthropic.client import ERROR_OUTPUT, AnthropicClient, ClaudeModel
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.utils.dates import local_now, verbose_datetime
from meeshbot.utils.flags import FlagKey, disable_flag, enable_flag


async def timeout(webhook: GroupMeWebhookPayload) -> None:
    if webhook.text is None:
        return

    body = webhook.text[len("/timeout") :].strip()

    client = GroupMeClient()

    if not body:
        await client.post_message(
            group_id=webhook.group_id,
            text="Do it like this IDIOT:\n`/timeout <how long>`\n`/timeout done`",
        )
        return

    if body.lower() == "done":
        await disable_flag(FlagKey.AI_RESPONSES_PAUSED)
        await client.post_message(
            group_id=webhook.group_id,
            text="I can speak again 🗣️",
        )
        return

    eta_iso = await AnthropicClient(model=ClaudeModel.OPUS).resolve_timestamp(body)

    if eta_iso.strip() == ERROR_OUTPUT:
        await client.post_message(
            group_id=webhook.group_id,
            text="I can't figure out when that is... IDIOT",
        )
        return

    eta = datetime.fromisoformat(eta_iso).replace(tzinfo=TIMEZONE)

    if eta <= local_now():
        await client.post_message(
            group_id=webhook.group_id,
            text="You can't put me in timeout in the past IDIOT",
        )
        return

    await enable_flag(FlagKey.AI_RESPONSES_PAUSED, expires_at=eta)

    await client.post_message(
        group_id=webhook.group_id,
        text=f"OK, shutting up until {verbose_datetime(eta)} 🤐",
    )
