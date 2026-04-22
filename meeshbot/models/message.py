from datetime import datetime

from oxyde import Field, Model

from meeshbot.models.group import GroupMeGroup
from meeshbot.models.user import GroupMeUser


class GroupMeMessage(Model):
    id: str = Field(db_pk=True)  # type:ignore[assignment]
    group: GroupMeGroup | None = Field(default=None, db_on_delete="SET NULL")  # type:ignore[assignment]
    sender: GroupMeUser | None = Field(default=None, db_on_delete="SET NULL")  # type:ignore[assignment]
    text: str | None = Field(default=None)  # type:ignore[assignment]
    system: bool = Field(default=False)  # type:ignore[assignment]
    attachments: list[dict] = Field(default_factory=list, db_type="JSONB")  # type:ignore[assignment]
    timestamp: datetime

    class Meta:
        is_table = True
