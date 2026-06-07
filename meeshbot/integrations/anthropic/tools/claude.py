from anthropic import types

WEBSEARCH_TOOL: types.WebSearchTool20260209Param = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 10,
}

WEBFETCH_TOOL: types.WebFetchTool20260209Param = {
    "type": "web_fetch_20260209",
    "name": "web_fetch",
    "max_uses": 5,
}
