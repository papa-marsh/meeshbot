from typing import Any, Literal

from pydantic import BaseModel


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


class OtherAttachment(BaseModel):
    """Catch-all for unknown attachment types GroupMe may introduce."""

    type: str
    model_config = {"extra": "allow"}

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return super().model_dump(**kwargs)


MessageAttachment = (
    ReplyAttachment | MentionsAttachment | ImageAttachment | VideoAttachment | OtherAttachment
)


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


class Member(BaseModel):
    id: str
    user_id: str
    nickname: str
    muted: bool
    image_url: str | None = None
    autokicked: bool
    app_installed: bool | None = None


class Group(BaseModel):
    id: str
    name: str
    type: str
    description: str
    image_url: str | None = None
    creator_user_id: str
    created_at: int
    updated_at: int
    members: list[Member]
    share_url: str | None = None


class Message(BaseModel):
    id: str
    source_guid: str
    created_at: int
    user_id: str
    group_id: str
    name: str
    avatar_url: str | None = None
    text: str | None = None
    system: bool
    favorited_by: list[str] = []
    attachments: list[MessageAttachment] = []
