from meeshbot.config import TESTING_GROUP_ID
from meeshbot.integrations.ai.client import AIClient
from meeshbot.integrations.ai.context import (
    SEND_AI_RESPONSE_CONTEXT,
    SHOULD_RESPOND_CONTEXT,
)
from meeshbot.integrations.ai.types import AIMessage, AIModel, Context
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.queries import get_message_history, is_public_group
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload
from meeshbot.models.user import GroupMeUser
from meeshbot.utils.logging import log
from meeshbot.utils.volume import get_response_threshold, get_volume

CHAT_HISTORY_MAX_DAYS = 14
CHAT_HISTORY_MAX_COUNT = 100

SHOULD_RESPOND_HISTORY_MAX_DAYS = 7
SHOULD_RESPOND_HISTORY_MAX_COUNT = 20


async def build_message_history(
    group_id: str,
    max_days: int = CHAT_HISTORY_MAX_DAYS,
    max_count: int = CHAT_HISTORY_MAX_COUNT,
) -> list[AIMessage]:
    context_messages: list[AIMessage] = []
    message_history_desc = await get_message_history(max_days, max_count, group_id=group_id)

    sender_name_map = {}

    for message in reversed(message_history_desc):
        user_id = message.sender_id or ""

        if user_id not in sender_name_map:
            user = await GroupMeUser.objects.get(id=user_id)
            sender_name_map[user_id] = user.name

        message_entry = AIClient.build_message_history_entry(
            sender_name=sender_name_map[user_id],
            timestamp=message.timestamp,
            message=message.text or "",
            attachments=message.attachments,
        )
        context_messages.append(message_entry)

    return context_messages


async def should_respond(group_id: str) -> bool:
    """
    Decide whether MeeshBot should respond to the most recent message.

    Builds a recent-history block, asks the classifier model for a 0-100
    likelihood score, and returns True if the score meets the threshold.
    """
    threshold = await get_response_threshold(group_id)
    message_history = await build_message_history(
        group_id=group_id,
        max_days=SHOULD_RESPOND_HISTORY_MAX_DAYS,
        max_count=SHOULD_RESPOND_HISTORY_MAX_COUNT,
    )

    prompt_lines = []
    for message in message_history[:-1]:
        prompt_lines.append(message["content"])

    prompt_lines.append("\n--- The message you are evaluating is: ---\n")
    most_recent_message = str(message_history[-1]["content"])
    prompt_lines.append(most_recent_message)

    client = AIClient(model=AIModel.BASIC)
    likelihood = await client.score_response_likelihood(
        history_text="\n".join(prompt_lines),
        context=SHOULD_RESPOND_CONTEXT,
    )

    log.info(
        "LLM response confidence determined",
        confidence=likelihood.score,
        threshold=threshold,
        reason=likelihood.reason,
        message=most_recent_message,
    )

    return likelihood.score >= threshold


async def send_ai_response(
    group_id: str = TESTING_GROUP_ID,
    trigger: GroupMeWebhookPayload | None = None,
) -> None:
    messages = await build_message_history(group_id)
    volume = await get_volume(group_id)

    messages.append(
        AIMessage(
            role="user",
            content=(
                "<-- Internal AI Note - not visible to user -->\n"
                f"<-- The current group ID is: {group_id} -->\n"
                f"<-- The current volume is: {volume:g}/10 -->"
            ),
        )
    )

    context = Context(
        group_id=group_id,
        sender_id=trigger.user_id if trigger is not None else None,
        trigger_message_id=trigger.id if trigger is not None else None,
    )

    allow_db_query = not is_public_group(group_id)
    response = await AIClient().generate_response(
        messages=messages,
        context=context,
        system_prompt=SEND_AI_RESPONSE_CONTEXT,
        allow_webfetch=True,
        allow_db_query=allow_db_query,
    )

    if not response:
        log.warning("AI response was empty, skipping GroupMe post", group_id=group_id)
        return

    await GroupMeClient().post_message(
        group_id=group_id,
        text=response,
    )
