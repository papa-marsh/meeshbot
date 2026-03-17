from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


async def whatissam(webhook: GroupMeWebhookPayload) -> None:
    await GroupMeClient().post_message(
        group_id=webhook.group_id,
        text="idk sounds like a bitch",
    )
