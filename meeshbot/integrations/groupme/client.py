from http import HTTPMethod
from typing import Any

import requests
from structlog.stdlib import get_logger

from meeshbot.config import GROUPME_TOKEN
from meeshbot.integrations.groupme.secrets import BOTS_BY_GROUP
from meeshbot.integrations.groupme.types import Group, Message, MessageAttachment

BASE_URL = "https://api.groupme.com/v3"

log = get_logger()


class GroupMeClient:
    def __init__(self, api_token: str | None = None) -> None:
        self.api_token = api_token or GROUPME_TOKEN

    @classmethod
    def get_bot_id(cls, group_id: str) -> str:
        return BOTS_BY_GROUP[group_id]

    def _get(self, path: str, params: dict[str, Any] | None = None) -> list | dict:
        url = f"{BASE_URL}{path}"
        params = {"token": self.api_token, **(params or {})}

        log.debug("Sending request to GroupMe", method=HTTPMethod.GET, url=url)
        response = requests.get(url, params, timeout=10)
        log.debug(
            "Received response from GroupMe",
            status=response.status_code,
            url=response.url.replace(GROUPME_TOKEN, "<token>"),
        )

        response.raise_for_status()
        data = response.json()["response"]

        if not isinstance(data, list | dict):
            raise TypeError

        return data

    def _post(self, path: str, json: dict[str, Any] | None = None) -> dict | None:
        url = f"{BASE_URL}{path}"
        params = {"token": self.api_token}

        log.debug("Sending request to GroupMe", method=HTTPMethod.POST, url=url)
        response = requests.post(url, params=params, json=json, timeout=10)
        log.debug(
            "Received response from GroupMe",
            status=response.status_code,
            url=response.url.replace(GROUPME_TOKEN, "<token>"),
        )

        response.raise_for_status()
        if not response.content:
            return None

        data = response.json().get("response")

        if not isinstance(data, dict | None):
            raise TypeError

        return data

    def post_message(
        self,
        group_id: str,
        text: str,
        attachments: list[MessageAttachment] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "bot_id": self.get_bot_id(group_id),
            "text": text,
        }
        if attachments:
            payload["attachments"] = [a.model_dump() for a in attachments]

        self._post("/bots/post", json=payload)

    def get_groups(self, page: int = 1, per_page: int = 100) -> list[Group]:
        params = {
            "page": page,
            "per_page": per_page,
        }
        data = self._get("/groups", params)

        return [Group.model_validate(g) for g in data]

    def get_group(self, group_id: str) -> Group:
        data = self._get(f"/groups/{group_id}")

        return Group.model_validate(data)

    def get_messages(
        self,
        group_id: str,
        before_id: str | None = None,
        since_id: str | None = None,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[Message]:
        params: dict[str, Any] = {"limit": limit}

        if before_id is not None:
            params["before_id"] = before_id
        if since_id is not None:
            params["since_id"] = since_id
        if after_id is not None:
            params["after_id"] = after_id

        data = self._get(f"/groups/{group_id}/messages", params=params)
        if not isinstance(data, dict):
            raise TypeError

        messages = data["messages"]

        if not isinstance(messages, list):
            raise TypeError

        return [Message.model_validate(m) for m in messages]
