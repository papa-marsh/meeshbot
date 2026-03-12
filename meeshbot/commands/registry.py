from collections.abc import Callable

from meeshbot.commands import ping
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

CommandFuncT = Callable[[GroupMeWebhookPayload], None]

COMMAND_REGISTRY: dict[str, CommandFuncT] = {
    "/ping": ping,
}


def get_command_func(command: str) -> CommandFuncT | None:
    func = COMMAND_REGISTRY.get(command, handle_invalid_command)

    return func


def handle_invalid_command(webhook: GroupMeWebhookPayload) -> None:
    text = "That's not a command IDIOT"
    GroupMeClient().post_message(group_id=webhook.group_id, text=text)
