from meeshbot.commands.registry import get_command_func
from meeshbot.integrations.groupme.queries import sync_message_to_db
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


async def handle_groupme_webhook(webhook: GroupMeWebhookPayload) -> None:
    await sync_message_to_db(webhook)

    if not webhook.text:
        return

    if webhook.text[0] == "/":
        message_parts = webhook.text.split(" ")
        command = message_parts[0]
        func = get_command_func(command)

        await func(webhook)
