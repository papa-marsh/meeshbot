from datetime import datetime

from meeshbot.config import TIMEZONE


def local_now() -> datetime:
    return datetime.now().astimezone(TIMEZONE)


def verbose_datetime(dt: datetime) -> str:
    local = dt.astimezone(TIMEZONE)
    return local.strftime("%A, %b %-d at %-I:%M %p %Z")
