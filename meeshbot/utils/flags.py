"""Persistent boolean flags with optional expiry, checked lazily on read."""

from datetime import datetime
from enum import StrEnum

from meeshbot.models import Flag
from meeshbot.utils.dates import local_now


class FlagKey(StrEnum):
    AI_RESPONSES_PAUSED = "ai_responses_paused"


async def enable_flag(key: FlagKey, expires_at: datetime | None = None) -> None:
    await _set_flag(key, value=True, expires_at=expires_at)


async def disable_flag(key: FlagKey) -> None:
    await _set_flag(key, value=False, expires_at=None)


async def flag_enabled(key: FlagKey) -> bool:
    flag = await Flag.objects.get_or_none(key=key.value)
    if flag is None or not flag.value:
        return False
    if flag.expires_at is not None and flag.expires_at <= local_now():
        await _set_flag(key, value=False, expires_at=None)
        return False
    return True


async def _set_flag(key: FlagKey, *, value: bool, expires_at: datetime | None) -> None:
    now = local_now()
    flag, created = await Flag.objects.get_or_create(
        key=key.value,
        defaults={"value": value, "expires_at": expires_at, "updated_at": now},
    )
    if not created:
        flag.value = value
        flag.expires_at = expires_at
        flag.updated_at = now
        await flag.save()
