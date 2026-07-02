from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

HELP_MESSAGE = """Command List:

/help: Shows this message.

/roll: Rolls any number of any-sided dice (eg. 4d20 rolls four 20-sided dice).

/remindme <when> - <message>: Send a reminder at a given day/time.

/reminders: List active reminders.

/timeout <how long>: Pause MeeshBot's AI replies (eg. /timeout for three hours).

/timeout done: Resume AI replies.

/scoreboard: Message count leaderboard"""


async def help(webhook: GroupMeWebhookPayload) -> None:
    await GroupMeClient().post_message(
        group_id=webhook.group_id,
        text=HELP_MESSAGE,
    )
