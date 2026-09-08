import asyncio
from datetime import UTC, datetime

from meeshbot.integrations.ai.client import AIClient
from meeshbot.integrations.ai.types import AIModel
from meeshbot.integrations.groupme.attachments import image_analysis_due
from meeshbot.integrations.groupme.types import ImageAnalysisStatus, ImageMetadata
from meeshbot.models import GroupMeMessage
from meeshbot.utils.logging import log

ANALYSIS_TIMEOUT_SECONDS = 120
_analysis_slots = asyncio.Semaphore(4)
# asyncio only holds weak task references; this keeps background work alive, not deduplicated.
_background_tasks: set[asyncio.Task[None]] = set()


async def dispatch_image_analysis(message_id: str) -> None:
    try:
        await _dispatch_image_analysis(message_id)
    except Exception:
        log.exception("Could not dispatch image analysis", message_id=message_id)


async def _dispatch_image_analysis(message_id: str) -> None:
    while (message := await GroupMeMessage.objects.get_or_none(id=message_id)) is not None:
        attachments = [dict(attachment) for attachment in message.attachments]
        pending: dict[str, ImageMetadata] = {}
        now = datetime.now(UTC)
        for attachment in attachments:
            url = attachment.get("url")
            if (
                attachment.get("type") != "image"
                or not isinstance(url, str)
                or not url
                or not image_analysis_due(attachment.get("metadata"), now)
            ):
                continue
            metadata = pending.setdefault(
                url, ImageMetadata(status=ImageAnalysisStatus.IN_PROGRESS, updated=now)
            )
            attachment["metadata"] = metadata.model_dump(mode="json", exclude_none=True)
        if not pending:
            return
        updated = await GroupMeMessage.objects.filter(
            id=message_id, attachments=message.attachments
        ).update(attachments=attachments)
        if not updated:
            continue
        for url, metadata in pending.items():
            task = asyncio.create_task(_analyze_image(message_id, url, metadata))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        return


async def _analyze_image(message_id: str, url: str, started: ImageMetadata) -> None:
    try:
        async with _analysis_slots:
            message = await GroupMeMessage.objects.get_or_none(id=message_id)
            expected = started.model_dump(mode="json", exclude_none=True)
            if message is None or not any(
                attachment.get("type") == "image"
                and attachment.get("url") == url
                and attachment.get("metadata") == expected
                for attachment in message.attachments
            ):
                return
            try:
                async with asyncio.timeout(ANALYSIS_TIMEOUT_SECONDS):
                    description = await AIClient(AIModel.CHEAP).describe_image(url)
                result = ImageMetadata(
                    status=ImageAnalysisStatus.COMPLETE,
                    updated=datetime.now(UTC),
                    description=description,
                )
            except Exception:
                log.exception("Image analysis failed", message_id=message_id)
                result = ImageMetadata(status=ImageAnalysisStatus.FAILED, updated=datetime.now(UTC))
            await _save_image_metadata(message_id, url, started, result)
    except Exception:
        log.exception("Could not persist image analysis", message_id=message_id)


async def _save_image_metadata(
    message_id: str, url: str, started: ImageMetadata, result: ImageMetadata
) -> None:
    expected = started.model_dump(mode="json", exclude_none=True)
    while (message := await GroupMeMessage.objects.get_or_none(id=message_id)) is not None:
        attachments = [dict(attachment) for attachment in message.attachments]
        changed = False
        for attachment in attachments:
            if (
                attachment.get("type") == "image"
                and attachment.get("url") == url
                and attachment.get("metadata") == expected
            ):
                attachment["metadata"] = result.model_dump(mode="json", exclude_none=True)
                changed = True
        if not changed:
            return
        if await GroupMeMessage.objects.filter(
            id=message_id, attachments=message.attachments
        ).update(attachments=attachments):
            return
