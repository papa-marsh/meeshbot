from meeshbot.integrations.ai.context import SET_VOLUME_TOOL_DESCRIPTION
from meeshbot.integrations.ai.types import ToolDefinition
from meeshbot.utils.volume import set_volume

SET_VOLUME_TOOL: ToolDefinition = {
    "name": "set_volume",
    "description": SET_VOLUME_TOOL_DESCRIPTION,
    "input_schema": {
        "type": "object",
        "properties": {
            "level": {
                "type": "string",
                "description": 'Target volume from 1 to 10, e.g. "7" or "1.5".',
            },
        },
        "required": ["level"],
        "additionalProperties": False,
    },
}


async def execute_set_volume(group_id: str, level: str) -> str:
    volume = await set_volume(group_id, level)
    return f"Volume set to {volume:g}/10."
