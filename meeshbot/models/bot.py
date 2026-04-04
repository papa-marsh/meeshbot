from oxyde import Field, Model

from meeshbot.models.group import GroupMeGroup


class GroupMeBot(Model):
    id: str = Field(db_pk=True)  # type:ignore[assignment]
    group: GroupMeGroup = Field(default=None, db_on_delete="CASCADE")  # type:ignore[assignment]

    class Meta:
        is_table = True
