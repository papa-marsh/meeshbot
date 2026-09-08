from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta

from meeshbot.integrations.groupme.types import ImageAnalysisStatus, MessageAttachment

IMAGE_ANALYSIS_RETRY_AFTER = timedelta(minutes=5)
STRUCTURAL_ATTACHMENT_TYPES = {"mentions", "reply"}


def serialize_attachments(attachments: Sequence[MessageAttachment]) -> list[dict[str, object]]:
    serialized = []
    for attachment in attachments:
        data = attachment.model_dump(mode="json")
        if attachment.type == "image":
            # Analysis metadata belongs to Meeshbot, not the incoming GroupMe payload.
            data.pop("metadata", None)
        serialized.append(data)
    return serialized


def merge_attachments(
    incoming: Sequence[Mapping[str, object]], stored: Sequence[Mapping[str, object]]
) -> list[dict[str, object]]:
    metadata_by_url = {
        attachment["url"]: attachment["metadata"]
        for attachment in stored
        if attachment.get("type") == "image"
        and isinstance(attachment.get("url"), str)
        and "metadata" in attachment
    }
    merged = []
    for attachment in incoming:
        data = dict(attachment)
        url = data.get("url")
        if data.get("type") == "image" and isinstance(url, str) and url in metadata_by_url:
            data["metadata"] = metadata_by_url[url]
        merged.append(data)
    return merged


def image_analysis_due(metadata: object, now: datetime) -> bool:
    if not isinstance(metadata, dict):
        return True
    if metadata.get("status") == ImageAnalysisStatus.COMPLETE:
        return False
    if metadata.get("status") != ImageAnalysisStatus.IN_PROGRESS:
        return True
    updated = metadata.get("updated")
    if not isinstance(updated, str):
        return True
    try:
        timestamp = datetime.fromisoformat(updated)
    except ValueError:
        return True
    if timestamp.tzinfo is None:
        return True
    return now - timestamp >= IMAGE_ANALYSIS_RETRY_AFTER


def render_attachments(attachments: Sequence[Mapping[str, object]]) -> str:
    lines = []
    for attachment in attachments:
        kind = attachment.get("type", "attachment")
        if not isinstance(kind, str) or kind in STRUCTURAL_ATTACHMENT_TYPES:
            continue
        if kind != "image":
            lines.append(f"[{kind.capitalize()}: Unable to analyze {kind} attachments]")
            continue
        metadata = attachment.get("metadata")
        description = "Not analyzed"
        if isinstance(metadata, dict):
            match metadata.get("status"):
                case ImageAnalysisStatus.COMPLETE:
                    description = metadata.get("description") or "Image analysis failed"
                case ImageAnalysisStatus.IN_PROGRESS:
                    description = "Analysis in progress"
                case ImageAnalysisStatus.FAILED:
                    description = "Image analysis failed"
        lines.append(f"[Image: {description}]")
    return "\n".join(lines)
