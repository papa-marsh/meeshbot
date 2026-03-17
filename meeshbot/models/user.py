from oxyde import Field, Model


class GroupMeUser(Model):
    id: str = Field(db_pk=True)
    name: str
    image_url: str | None = Field(default=None)
    muted: bool = Field(default=False)

    class Meta:
        is_table = True
