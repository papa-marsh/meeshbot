from oxyde import Field, Model

from meeshbot.models.group import GroupMeGroup


class GroupMeBot(Model):
    id: str = Field(db_pk=True)
    group: GroupMeGroup | None = Field(default=None, db_on_delete="CASCADE")

    class Meta:
        is_table = True
