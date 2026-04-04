from datetime import datetime

from oxyde import Field, Model


class GroupMeGroup(Model):
    id: str = Field(db_pk=True)  # type:ignore[assignment]
    name: str
    image_url: str | None = Field(default=None)  # type:ignore[assignment]
    created_at: datetime

    class Meta:
        is_table = True
