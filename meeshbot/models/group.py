from datetime import datetime

from oxyde import Field, Model


class GroupMeGroup(Model):
    id: str = Field(db_pk=True)  # type:ignore[assignment]
    name: str
    image_url: str | None = Field(default=None)  # type:ignore[assignment]
    created_at: datetime
    response_threshold: float = Field(default=50.0)  # type:ignore[assignment]

    class Meta:
        is_table = True
