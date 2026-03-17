from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

HELP_MESSAGE = """Command List:

/help: Shows this message.

/roll: Rolls any number of any-sided dice (eg. 4d20 rolls four 20-sided dice)."""


async def help(webhook: GroupMeWebhookPayload) -> None:
    await GroupMeClient().post_message(
        group_id=webhook.group_id,
        text=HELP_MESSAGE,
    )
