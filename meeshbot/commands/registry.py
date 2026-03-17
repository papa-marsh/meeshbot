from collections.abc import Awaitable, Callable

from meeshbot.commands import help, ping, roll, whatisjeff, whatissam
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

CommandFuncT = Callable[[GroupMeWebhookPayload], Awaitable[None]]

COMMAND_REGISTRY: dict[str, CommandFuncT] = {
    "/help": help,
    "/ping": ping,
    "/roll": roll,
    "/whatissam": whatissam,
    "/whatisjeff": whatisjeff,
}


def get_command_func(command: str) -> CommandFuncT:
    return COMMAND_REGISTRY.get(command, handle_invalid_command)


async def handle_invalid_command(webhook: GroupMeWebhookPayload) -> None:
    await GroupMeClient().post_message(
        group_id=webhook.group_id,
        text="That's not a command IDIOT",
    )
