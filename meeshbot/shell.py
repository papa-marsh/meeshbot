"""
Interactive shell with pre-loaded meeshbot context.
Run with: make shell
"""

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

from oxyde import db

from meeshbot.config import DATABASE_URL, TESTING_GROUP_ID, TIMEZONE
from meeshbot.integrations.ai import chat as ai_chat
from meeshbot.integrations.ai.chat import build_message_history, send_ai_response
from meeshbot.integrations.ai.client import AIClient
from meeshbot.integrations.ai.types import AIMessage
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.models import GroupMeGroup, GroupMeMessage, GroupMeUser, Reminder
from meeshbot.utils.logging import log

asyncio.run(db.init(default=DATABASE_URL))

groupme = GroupMeClient()
ai = AIClient()


async def mock_ai_response(
    message: str,
    group_id: str = TESTING_GROUP_ID,
) -> None:
    """Trigger the AI response pipeline without sending anything to GroupMe"""

    async def _build_message_history_with_injection(gid: str, **kwargs: Any) -> list[AIMessage]:
        history = await build_message_history(gid, **kwargs)
        history.append(
            AIClient.build_message_history_entry(
                sender_name="Marshall",
                timestamp=datetime.now(tz=TIMEZONE),
                message=message,
            )
        )
        return history

    with (
        patch.object(
            ai_chat,
            "build_message_history",
            side_effect=_build_message_history_with_injection,
        ),
        patch.object(GroupMeClient, "post_message", new=AsyncMock()),
    ):
        await send_ai_response(group_id)
