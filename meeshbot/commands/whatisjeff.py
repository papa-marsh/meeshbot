from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


def whatisjeff(webhook: GroupMeWebhookPayload) -> None:
    text = "Oh, you mean Brad?"
    GroupMeClient().post_message(group_id=webhook.group_id, text=text)
