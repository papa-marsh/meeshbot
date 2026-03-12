import random
import re

from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

ROLL_PATTERN = re.compile(r"^(\d+)d(\d+)$", re.IGNORECASE)


def roll(webhook: GroupMeWebhookPayload) -> None:
    if webhook.text is None:
        return

    args = webhook.text.split()
    if len(args) < 2:
        GroupMeClient().post_message(
            group_id=webhook.group_id, text="That's not a valid dice roll format dumb ass"
        )
        return

    match = ROLL_PATTERN.match(args[1])
    if not match:
        GroupMeClient().post_message(
            group_id=webhook.group_id, text="That's not a valid dice roll format dumb ass"
        )
        return

    num_dice = int(match.group(1))
    num_sides = int(match.group(2))

    if num_dice <= 0 or num_sides <= 0:
        GroupMeClient().post_message(
            group_id=webhook.group_id,
            text="Are you stupid? The numbers need to be greater than zero",
        )
        return

    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    total = sum(rolls)

    text = f"{num_dice}d{num_sides} rolled {total} ({', '.join(str(r) for r in rolls)})"
    GroupMeClient().post_message(group_id=webhook.group_id, text=text)
