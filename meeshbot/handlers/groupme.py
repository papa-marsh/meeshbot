from meeshbot.commands.registry import get_command_func
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


def handle_groupme_webhook(webhook: GroupMeWebhookPayload) -> None:
    if webhook.text is None:
        return

    if webhook.text[0] == "/":
        message_parts = webhook.text.split(" ")
        command = message_parts[0]
        func = get_command_func(command)

        func(webhook)
