import json

import asyncpg

from meeshbot.config import AI_DATABASE_URL
from meeshbot.integrations.ai.context import DB_QUERY_TOOL_DESCRIPTION
from meeshbot.integrations.ai.types import ToolDefinition
from meeshbot.utils.logging import log

DB_QUERY_TOOL: ToolDefinition = {
    "name": "query_database",
    "description": DB_QUERY_TOOL_DESCRIPTION,
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": (
                    "A read-only SELECT query to execute. Must not contain any data-mutating "
                    "statements (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, etc.)."
                ),
            }
        },
        "required": ["sql"],
        "additionalProperties": False,
    },
}

ERROR_PREFIX = "Error:"

_DISALLOWED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "vacuum",
    "reindex",
}


def _is_safe_query(sql: str) -> bool:
    normalized = sql.lower()
    return not any(keyword in normalized for keyword in _DISALLOWED_KEYWORDS)


async def execute_db_query(sql: str) -> str:
    """
    Execute a read-only SELECT query against the database using the AI read-only user.

    Returns a JSON string of results on success, or an error string on failure.
    The caller is responsible for passing is_error=True to the tool_result when
    this function raises or returns an error-prefixed string.
    """
    if not _is_safe_query(sql):
        return f"{ERROR_PREFIX} query contains disallowed keywords. Only SELECTs are permitted."

    log.info("AI executing database query", sql=sql)

    conn: asyncpg.Connection = await asyncpg.connect(AI_DATABASE_URL)
    try:
        rows = await conn.fetch(sql)
        return json.dumps([dict(row) for row in rows], default=str)
    finally:
        await conn.close()
