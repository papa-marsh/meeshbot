import functools
from collections.abc import Awaitable, Callable

from meeshbot.commands import help, ping, roll, scoreboard, sync, whatisjeff, whatissam
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.secrets import ADMIN_USER_IDS, PUBLIC_GROUPS
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

CommandFuncT = Callable[[GroupMeWebhookPayload], Awaitable[None]]


def admin_only(func: CommandFuncT) -> CommandFuncT:
    @functools.wraps(func)
    async def wrapper(webhook: GroupMeWebhookPayload) -> None:
        if webhook.user_id not in ADMIN_USER_IDS:
            await GroupMeClient().post_message(
                group_id=webhook.group_id,
                text="You're not allowed to do that IDIOT",
            )
            return
        await func(webhook)

    return wrapper


def no_public(func: CommandFuncT) -> CommandFuncT:
    @functools.wraps(func)
    async def wrapper(webhook: GroupMeWebhookPayload) -> None:
        if webhook.group_id in PUBLIC_GROUPS:
            await GroupMeClient().post_message(
                group_id=webhook.group_id,
                text="You can't do that here IDIOT",
            )
            return
        await func(webhook)

    return wrapper


COMMAND_REGISTRY: dict[str, CommandFuncT] = {
    "/help": help,
    "/ping": ping,
    "/adminping": admin_only(ping),
    "/roll": roll,
    "/scoreboard": scoreboard,
    "/sync": no_public(admin_only(sync)),
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
