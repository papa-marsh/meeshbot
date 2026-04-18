from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.queries import MessageCount, get_message_counts
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def _format_entry(rank: int, entry: MessageCount) -> str:
    prefix = MEDALS.get(rank, f"{rank}.")
    return f"{prefix} {entry['name']} | {entry['count']}"


async def scoreboard(webhook: GroupMeWebhookPayload) -> None:
    counts = await get_message_counts(webhook.group_id)

    if not counts:
        await GroupMeClient().post_message(
            group_id=webhook.group_id,
            text="No messages found for this group.",
        )
        return

    lines = ["🏆 Message Count Leaderboard 🏆\n"]
    for i, entry in enumerate(counts, start=1):
        lines.append(_format_entry(i, entry))

    await GroupMeClient().post_message(
        group_id=webhook.group_id,
        text="\n".join(lines),
    )
