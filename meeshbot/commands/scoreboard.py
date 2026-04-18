from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.queries import MessageCount, get_message_counts
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


def _rank_emoji(rank: int) -> str:
    if rank == 1:
        return "🥇"
    if rank == 2:
        return "🥈"
    if rank == 3:
        return "🥉"
    if 4 <= rank <= 9:
        return f"{rank}\ufe0f\u20e3"
    return "#️⃣"


def _format_entry(rank: int, entry: MessageCount) -> str:
    return f"{_rank_emoji(rank)} {entry['name']} | {entry['count']}"


async def scoreboard(webhook: GroupMeWebhookPayload) -> None:
    counts = await get_message_counts(webhook.group_id)
    await _post_scoreboard(webhook, counts, title="🏆 Message Count Leaderboard 🏆")


async def scoreboard_all(webhook: GroupMeWebhookPayload) -> None:
    counts = await get_message_counts()
    await _post_scoreboard(webhook, counts, title="🏆 All-Time Message Count Leaderboard 🏆")


async def _post_scoreboard(
    webhook: GroupMeWebhookPayload, counts: list[MessageCount], title: str
) -> None:
    if not counts:
        await GroupMeClient().post_message(
            group_id=webhook.group_id,
            text="No messages found.",
        )
        return

    lines = [f"{title}\n"]
    for i, entry in enumerate(counts, start=1):
        lines.append(_format_entry(i, entry))

    await GroupMeClient().post_message(
        group_id=webhook.group_id,
        text="\n".join(lines),
    )
