from oxyde import Field, Model


class GroupMeUser(Model):
    id: str = Field(db_pk=True)  # type:ignore[assignment]
    name: str
    image_url: str | None = Field(default=None)  # type:ignore[assignment]
    muted: bool = Field(default=False)  # type:ignore[assignment]

    class Meta:
        is_table = True
