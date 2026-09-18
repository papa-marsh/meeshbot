from meeshbot.integrations.ai.context import CREATE_REMINDER_TOOL_DESCRIPTION
from meeshbot.integrations.ai.tools.db import ERROR_PREFIX
from meeshbot.integrations.ai.types import Context, ToolDefinition
from meeshbot.utils.dates import verbose_datetime
from meeshbot.utils.logging import log
from meeshbot.utils.reminders import PastTimeError, UnresolvableTimeError, create_reminder

CREATE_REMINDER_TOOL: ToolDefinition = {
    "name": "create_reminder",
    "description": CREATE_REMINDER_TOOL_DESCRIPTION,
    "input_schema": {
        "type": "object",
        "properties": {
            "time": {
                "type": "string",
                "description": (
                    "Natural-language description of when the reminder should fire, "
                    'e.g. "tomorrow at 3pm", "next friday morning", "in 2 hours".'
                ),
            },
            "message": {
                "type": "string",
                "description": "The reminder body text delivered when the reminder fires.",
            },
        },
        "required": ["time", "message"],
        "additionalProperties": False,
    },
}


async def execute_create_reminder(
    context: Context,
    time_description: str,
    message: str,
) -> str:
    """
    Create a reminder on behalf of the sender of the triggering message.

    Returns a confirmation string with the resolved delivery time, or an
    error-prefixed string when the time description can't be resolved.
    """
    if context.sender_id is None or context.trigger_message_id is None:
        raise ValueError("Reminder creation requires sender and triggering message IDs")

    log.info(
        "AI creating reminder",
        group_id=context.group_id,
        sender_id=context.sender_id,
        time_description=time_description,
        message=message,
    )

    try:
        eta = await create_reminder(
            group_id=context.group_id,
            sender_id=context.sender_id,
            trigger_message_id=context.trigger_message_id,
            message=message,
            time_description=time_description,
        )
    except UnresolvableTimeError:
        return f"{ERROR_PREFIX} could not resolve {time_description!r} to a timestamp."
    except PastTimeError:
        return f"{ERROR_PREFIX} {time_description!r} resolves to a time in the past."

    return f"Reminder created. It will be delivered on {verbose_datetime(eta)}."
