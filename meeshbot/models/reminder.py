from datetime import datetime

from oxyde import Field, Model

from meeshbot.models.group import GroupMeGroup
from meeshbot.models.user import GroupMeUser


class Reminder(Model):
    id: str = Field(db_pk=True)  # type:ignore[assignment]
    group: GroupMeGroup = Field(db_on_delete="CASCADE")  # type:ignore[assignment]
    sender: GroupMeUser = Field(db_on_delete="CASCADE")  # type:ignore[assignment]
    command_message_id: str
    message: str
    eta: datetime
    created_at: datetime
    sent: bool = Field(default=False)  # type:ignore[assignment]

    class Meta:
        is_table = True
