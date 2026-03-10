from datetime import datetime

from meeshbot.config import TIMEZONE


def local_now() -> datetime:
    return datetime.now().astimezone(TIMEZONE)
