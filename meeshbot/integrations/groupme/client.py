from datetime import datetime, timedelta, timezone

import requests
from structlog.stdlib import get_logger

from meeshbot import config
from meeshbot.integrations.groupme.db import get_bot_id, get_group_ids, sync_message_to_db
from meeshbot.integrations.groupme.types import (
    GroupMeAPIResponse,
    GroupMeMessage,
    Mention,
    MentionsAttachment,
    MessageAttachment,
    ReplyAttachment,
)

BASE_URL = "https://api.groupme.com/v3"

log = get_logger()


def send_message(
    group_id: str,
    message: str,
    mentions: list[Mention] | None = None,
    reply_to: str | None = None,
) -> None:
    if mentions is None:
        mentions = []

    attachments: list[MessageAttachment] = []

    if reply_to:
        attachments.append(ReplyAttachment(type="reply", reply_id=reply_to, base_reply_id=reply_to))

    if mentions:
        attachments.append(
            MentionsAttachment(
                type="mentions",
                user_ids=[m.user_id for m in mentions],
                loci=[(m.index, m.length) for m in mentions],
            )
        )

    payload = {
        "text": message,
        "bot_id": get_bot_id(group_id),
        "attachments": [a.model_dump() for a in attachments],
    }

    response = requests.post(f"{BASE_URL}/bots/post", json=payload, timeout=10)
    if not response.ok:
        log.error("Error sending message: %s", response.text)


def get_messages(group_id: str, before_id: str | None = None) -> list[GroupMeMessage]:
    params: dict[str, str | int] = {"token": config.GROUPME_TOKEN, "limit": 25}
    if before_id is not None:
        params["before_id"] = before_id

    response = requests.get(f"{BASE_URL}/groups/{group_id}/messages", params=params, timeout=10)

    if response.status_code == 304:
        return []
    response.raise_for_status()

    return GroupMeAPIResponse.model_validate(response.json()).response.messages


def periodic_message_sync(hours_to_sync: int) -> None:
    log.info("Syncing messages from the last %d hours...", hours_to_sync)
    group_ids = get_group_ids()
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours_to_sync)

    for group_id in group_ids:
        log.info("Syncing messages for group: %s", group_id)
        try:
            after_id: str | None = None
            has_more = True

            while has_more:
                params: dict[str, str | int] = {"token": config.GROUPME_TOKEN, "limit": 100}
                if after_id:
                    params["after_id"] = after_id

                response = requests.get(
                    f"{BASE_URL}/groups/{group_id}/messages", params=params, timeout=10
                )

                if response.status_code == 304:
                    log.info("Received 304. No more messages.")
                    break

                response.raise_for_status()

                messages = GroupMeAPIResponse.model_validate(response.json()).response.messages

                if not messages:
                    has_more = False
                    continue

                # Stop once we've passed the cutoff
                oldest = datetime.fromtimestamp(messages[0].created_at, tz=timezone.utc)
                if oldest < cutoff:
                    messages = [
                        m
                        for m in messages
                        if datetime.fromtimestamp(m.created_at, tz=timezone.utc) >= cutoff
                    ]
                    has_more = False

                log.info("Syncing %d messages", len(messages))
                for message in messages:
                    sync_message_to_db(message)

                after_id = messages[-1].id

        except Exception:
            log.exception("Error syncing messages for group %s", group_id)
