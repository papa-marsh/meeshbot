from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ReplyAttachment(BaseModel):
    type: Literal["reply"]
    reply_id: str
    base_reply_id: str


class MentionsAttachment(BaseModel):
    type: Literal["mentions"]
    user_ids: list[str]
    loci: list[tuple[int, int]]


class ImageAttachment(BaseModel):
    type: Literal["image"]
    url: str
    blur_hash: str | None = None


class VideoAttachment(BaseModel):
    type: Literal["video"]
    url: str
    preview_url: str | None = None
    blur_hash: str | None = None


MessageAttachment = Annotated[
    ReplyAttachment | MentionsAttachment | ImageAttachment | VideoAttachment,
    Field(discriminator="type"),
]


class GroupMeWebhookPayload(BaseModel):
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
    attachments: list[MessageAttachment] = []
