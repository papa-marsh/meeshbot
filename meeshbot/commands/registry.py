import functools
from collections.abc import Awaitable, Callable

from meeshbot.commands import (
    help,
    ping,
    reminders,
    remindme,
    roll,
    scoreboard,
    scoreboard_all,
    sync,
    what_is_jeff,
    what_is_sam,
)
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.queries import is_admin_user, is_public_group
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

CommandFuncT = Callable[[GroupMeWebhookPayload], Awaitable[None]]


def admin_only(func: CommandFuncT) -> CommandFuncT:
    @functools.wraps(func)
    async def wrapper(webhook: GroupMeWebhookPayload) -> None:
        if not is_admin_user(webhook.user_id):
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
        if is_public_group(webhook.group_id):
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
    "/admin-ping": admin_only(ping),
    "/remindme": remindme,
    "/reminders": reminders,
    "/roll": roll,
    "/scoreboard": scoreboard,
    "/scoreboard-all": no_public(scoreboard_all),
    "/sync": no_public(admin_only(sync)),
    "/whatissam": what_is_sam,
    "/whatisjeff": what_is_jeff,
}


def get_command_func(command: str) -> CommandFuncT:
    return COMMAND_REGISTRY.get(command, handle_invalid_command)


async def handle_invalid_command(webhook: GroupMeWebhookPayload) -> None:
    await GroupMeClient().post_message(
        group_id=webhook.group_id,
        text="That's not a command IDIOT",
    )
