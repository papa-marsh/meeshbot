from oxyde import Field, Model


class GroupMeGroup(Model):
    id: str = Field(db_pk=True)
    name: str
    image_url: str | None = Field(default=None)
    created_at: int
    members: dict = Field(default_factory=dict, db_type="JSONB")

    class Meta:
        is_table = True
