from meeshbot.commands.registry import get_command_func
from meeshbot.integrations.ai.chat import send_ai_response, should_respond
from meeshbot.integrations.groupme.queries import sync_message_to_db
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.utils.flags import FlagKey, flag_enabled


async def handle_groupme_webhook(webhook: GroupMeWebhookPayload) -> None:
    await sync_message_to_db(webhook)

    if webhook.text and webhook.text[0] == "/":
        await _handle_slash_command(webhook)

    if webhook.text and not webhook.text.startswith("/") and webhook.name != "MeeshBot":
        await _handle_ai_response(webhook)


async def _handle_slash_command(webhook: GroupMeWebhookPayload) -> None:
    if not webhook.text:
        raise ValueError

    message_parts = webhook.text.split(" ")
    command = message_parts[0]
    func = get_command_func(command)

    await func(webhook)


async def _handle_ai_response(webhook: GroupMeWebhookPayload) -> None:
    if await flag_enabled(FlagKey.AI_RESPONSES_PAUSED):
        return

    if await should_respond(webhook.group_id):
        await send_ai_response(webhook.group_id, trigger=webhook)
