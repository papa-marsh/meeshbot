"""Database utilities for GroupMe integration."""

from meeshbot.integrations.groupme.types import GroupMeWebhookPayload


def get_bot_id(group_id: str) -> str:
    """Return the bot ID for the given group."""
    raise NotImplementedError


def get_group_ids() -> list[str]:
    """Return all configured group IDs."""
    raise NotImplementedError


def sync_message_to_db(message: GroupMeWebhookPayload) -> None:
    """Persist a GroupMe message to the database."""
    raise NotImplementedError
