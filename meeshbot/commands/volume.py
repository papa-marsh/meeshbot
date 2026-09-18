from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.utils.volume import get_volume, set_volume


async def volume(webhook: GroupMeWebhookPayload) -> None:
    args = (webhook.text or "").split()
    if len(args) == 1:
        level = await get_volume(webhook.group_id)
        text = f"Volume is {level:g}/10. Use /volume <1-10> to change it."
    elif len(args) == 2:
        try:
            level = await set_volume(webhook.group_id, args[1])
        except ValueError as exc:
            text = str(exc)
        else:
            text = f"Volume set to {level:g}/10."
    else:
        text = "Usage: /volume [1-10] (decimals allowed)."

    await GroupMeClient().post_message(group_id=webhook.group_id, text=text)
