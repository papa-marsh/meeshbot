from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


def whatissam(webhook: GroupMeWebhookPayload) -> None:
    text = "idk sounds like a bitch"
    GroupMeClient().post_message(group_id=webhook.group_id, text=text)
