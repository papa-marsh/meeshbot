import math

from meeshbot.models import GroupMeGroup
from meeshbot.utils.logging import log

INVALID_VOLUME_MESSAGE = "Volume must be a number from 1 to 10 (decimals allowed)."


async def get_response_threshold(group_id: str) -> float:
    group = await GroupMeGroup.objects.get(id=group_id)
    return group.response_threshold


async def get_volume(group_id: str) -> float:
    return (100 - await get_response_threshold(group_id)) / 10


async def set_volume(group_id: str, value: str) -> float:
    try:
        level = float(value)
    except ValueError as exc:
        raise ValueError(INVALID_VOLUME_MESSAGE) from exc
    if not math.isfinite(level) or not 1 <= level <= 10:
        raise ValueError(INVALID_VOLUME_MESSAGE)

    group = await GroupMeGroup.objects.get(id=group_id)
    group.response_threshold = 100 - level * 10
    await group.save(update_fields={"response_threshold"})
    log.info(
        "Volume changed",
        group_id=group_id,
        volume=level,
        response_threshold=group.response_threshold,
    )
    return level
