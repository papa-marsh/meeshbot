from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


def ping(webhook: GroupMeWebhookPayload) -> None:
    text = "pong"
    GroupMeClient().post_message(group_id=webhook.group_id, text=text)
