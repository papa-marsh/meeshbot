from datetime import datetime

from oxyde import Field, Model

from meeshbot.models.group import GroupMeGroup
from meeshbot.models.user import GroupMeUser


class Reminder(Model):
    id: str = Field(db_pk=True)  # type:ignore[assignment]
    group: GroupMeGroup | None = Field(default=None, db_on_delete="SET NULL")  # type:ignore[assignment]
    sender: GroupMeUser | None = Field(default=None, db_on_delete="SET NULL")  # type:ignore[assignment]
    command_message_id: str
    message: str
    eta: datetime
    created_at: datetime
    sent: bool = Field(default=False)  # type:ignore[assignment]

    class Meta:
        is_table = True
