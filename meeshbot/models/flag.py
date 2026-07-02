from datetime import datetime

from oxyde import Field, Model


class Flag(Model):
    key: str = Field(db_pk=True)  # type:ignore[assignment]
    value: bool
    expires_at: datetime | None = Field(default=None)  # type:ignore[assignment]
    updated_at: datetime

    class Meta:
        is_table = True
