from oxyde import Field, Model

from meeshbot.models.group import GroupMeGroup
from meeshbot.models.user import GroupMeUser


class GroupMeMessage(Model):
    id: str = Field(db_pk=True)
    group: GroupMeGroup | None = Field(default=None, db_on_delete="CASCADE")
    sender: GroupMeUser | None = Field(default=None, db_on_delete="SET NULL")
    text: str | None = Field(default=None)
    system: bool = Field(default=False)
    attachments: list = Field(default_factory=list, db_type="JSONB")
    timestamp: int

    class Meta:
        is_table = True
