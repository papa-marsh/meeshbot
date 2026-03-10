from typing import Annotated, Literal

from pydantic import BaseModel


class GroupMeMessage(BaseModel):
    id: str
    created_at: int
    sender_id: str
    sender_type: str
    source_guid: str
    system: bool
    text: str | None = None
    user_id: str
    name: str
    group_id: str
    avatar_url: str | None = None
    attachments: list[dict] = []


class GroupMeAPIResponseMeta(BaseModel):
    code: int


class GroupMeAPIResponseBody(BaseModel):
    count: int
    messages: list[GroupMeMessage]


class GroupMeAPIResponse(BaseModel):
    meta: GroupMeAPIResponseMeta
    response: GroupMeAPIResponseBody


class Mention(BaseModel):
    user_id: str
    index: int
    length: int


class ReplyAttachment(BaseModel):
    type: Literal["reply"]
    reply_id: str
    base_reply_id: str


class MentionsAttachment(BaseModel):
    type: Literal["mentions"]
    user_ids: list[str]
    loci: list[tuple[int, int]]


MessageAttachment = Annotated[ReplyAttachment | MentionsAttachment, ...]
