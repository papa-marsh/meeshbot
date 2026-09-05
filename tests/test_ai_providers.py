import asyncio
import json
from collections.abc import Sequence
from unittest.mock import AsyncMock

import httpx
import httpx2
import pytest
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel

from meeshbot.integrations.ai.provider import AIProvider
from meeshbot.integrations.ai.providers import anthropic, openai
from meeshbot.integrations.ai.tools.db import DB_QUERY_TOOL
from meeshbot.integrations.ai.types import AIMessage, AIModel, AITool


class Answer(BaseModel):
    answer: str


def response_payload(
    provider: str, output: list[dict[str, object]], *, status: str = "done"
) -> dict[str, object]:
    if provider == "anthropic":
        return {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-5",
            "content": output,
            "stop_reason": {"done": "end_turn", "tools": "tool_use"}.get(status, status),
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 10},
        }
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1,
        "model": "gpt-5.6-terra",
        "output": output,
        "status": "completed" if status in {"done", "tools"} else status,
        "error": None,
        "incomplete_details": None,
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
    }


def text_output(provider: str, text: str) -> dict[str, object]:
    if provider == "anthropic":
        return {"type": "text", "text": text}
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


def tool_call(provider: str, name: str, arguments: object, call_id: str) -> dict[str, object]:
    if provider == "anthropic":
        return {"type": "tool_use", "id": call_id, "name": name, "input": arguments}
    return {
        "type": "function_call",
        "id": f"item_{call_id}",
        "call_id": call_id,
        "name": name,
        "arguments": json.dumps(arguments),
        "status": "completed",
    }


def install_api(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    responses: Sequence[dict[str, object]],
    requests: list[dict[str, object]],
    model: AIModel = AIModel.BASIC,
) -> AIProvider:
    payloads = iter(responses)
    if provider == "anthropic":

        def handle_anthropic(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=next(payloads))

        sdk = AsyncAnthropic(
            api_key="test",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle_anthropic)),
        )
        monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **_kwargs: sdk)
        return anthropic.AnthropicProvider(model, api_key="test")

    def handle_openai(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(200, json=next(payloads))

    sdk_openai = AsyncOpenAI(
        api_key="test",
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle_openai)),
    )
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_kwargs: sdk_openai)
    return openai.OpenAIProvider(model, api_key="test")


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_tool_continuation_preserves_history_and_returns_final_text(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    requests: list[dict[str, object]] = []
    first_output = [
        text_output(provider, "Looking it up."),
        tool_call(provider, "query_database", {"sql": "SELECT 1"}, "call_query"),
        tool_call(provider, "unavailable", {}, "call_unknown"),
    ]
    reasoning: dict[str, object] = (
        {"type": "thinking", "thinking": "Plan", "signature": "signed"}
        if provider == "anthropic"
        else {"type": "reasoning", "id": "rs_test", "summary": [], "encrypted_content": "encrypted"}
    )
    first_output.insert(0, reasoning)
    adapter = install_api(
        monkeypatch,
        provider,
        [
            response_payload(provider, first_output, status="tools"),
            response_payload(provider, [text_output(provider, "The answer is 1.")]),
        ],
        requests,
    )
    execute = AsyncMock(return_value='[{"value": 1}]')
    messages: list[AIMessage] = [
        {"role": "user", "content": "Who won?"},
        {"role": "assistant", "content": "Let me check."},
    ]
    result = asyncio.run(
        adapter.generate_response(
            messages,
            context="Be concise",
            max_tokens=2048,
            tools=[AITool(DB_QUERY_TOOL, execute)],
            allow_web=True,
        )
    )
    assert result == "The answer is 1."
    assert len(messages) == 2
    execute.assert_awaited_once_with({"sql": "SELECT 1"})
    assert len(requests) == 2
    if provider == "anthropic":
        history = requests[1]["messages"]
        assert history[:2] == messages
        assert history[2]["content"] == first_output
        results = history[3]["content"]
        assert results[0]["tool_use_id"] == "call_query"
        assert results[0]["content"] == '[{"value": 1}]'
        assert results[1]["tool_use_id"] == "call_unknown"
        assert results[1]["is_error"] is True
    else:
        history = requests[1]["input"]
        assert history[:2] == messages
        assert reasoning in history
        results = [item for item in history if item.get("type") == "function_call_output"]
        assert results[0]["call_id"] == "call_query"
        assert results[0]["output"] == '[{"value": 1}]'
        assert results[1]["call_id"] == "call_unknown"
        assert results[1]["output"].startswith("Error:")
        assert all(request["store"] is False for request in requests)
        assert all(request["instructions"] == "Be concise" for request in requests)


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_structured_output_is_parsed_by_sdk(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    requests: list[dict[str, object]] = []
    adapter = install_api(
        monkeypatch,
        provider,
        [
            response_payload(provider, [text_output(provider, '{"answer":"tomorrow"}')]),
        ],
        requests,
    )
    result = asyncio.run(
        adapter.generate_structured(
            "When?",
            context="Resolve time",
            output_format=Answer,
            max_tokens=200,
        )
    )
    assert result == Answer(answer="tomorrow")
    request = requests[0]
    if provider == "anthropic":
        assert request["output_config"]["format"]["schema"]["required"] == ["answer"]
        assert request["thinking"] == {"type": "disabled"}
    else:
        assert request["text"]["format"]["schema"]["required"] == ["answer"]
        assert request["reasoning"] == {"effort": "none"}
        assert request["store"] is False


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
@pytest.mark.parametrize("status", ["done", "incomplete"])
def test_missing_or_incomplete_structured_output_raises(
    monkeypatch: pytest.MonkeyPatch, provider: str, status: str
) -> None:
    native_status = "max_tokens" if provider == "anthropic" and status == "incomplete" else status
    adapter = install_api(
        monkeypatch, provider, [response_payload(provider, [], status=native_status)], []
    )
    with pytest.raises(ValueError):
        asyncio.run(
            adapter.generate_structured(
                "When?",
                context="Resolve time",
                output_format=Answer,
                max_tokens=64,
            )
        )


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_frontier_structured_calls_allow_for_mandatory_reasoning(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    requests: list[dict[str, object]] = []
    adapter = install_api(
        monkeypatch,
        provider,
        [
            response_payload(provider, [text_output(provider, '{"answer":"yes"}')]),
        ],
        requests,
        model=AIModel.FRONTIER,
    )
    asyncio.run(
        adapter.generate_structured(
            "Question", context="Context", output_format=Answer, max_tokens=64
        )
    )
    if provider == "anthropic":
        assert requests[0]["model"] == "claude-fable-5-1"
        assert requests[0]["max_tokens"] >= 8192
        assert requests[0]["thinking"] == {"type": "adaptive"}
        assert requests[0]["output_config"]["effort"] == "low"
    else:
        assert requests[0]["model"] == "gpt-6-astra"
        assert requests[0]["max_output_tokens"] >= 8192
        assert requests[0]["reasoning"] == {"effort": "low"}


def test_anthropic_resumes_server_tool_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict[str, object]] = []
    paused_output = [text_output("anthropic", "Searching.")]
    adapter = install_api(
        monkeypatch,
        "anthropic",
        [
            response_payload("anthropic", paused_output, status="pause_turn"),
            response_payload("anthropic", [text_output("anthropic", "Found it.")]),
        ],
        requests,
        model=AIModel.CHEAP,
    )
    result = asyncio.run(
        adapter.generate_response(
            [{"role": "user", "content": "Search"}],
            context="Context",
            max_tokens=2048,
            tools=[],
            allow_web=True,
        )
    )
    assert result == "Found it."
    assert requests[1]["messages"][-1] == {"role": "assistant", "content": paused_output}
    assert all(tool["allowed_callers"] == ["direct"] for tool in requests[0]["tools"])


def test_openai_renders_citation_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    output = {
        "id": "msg_cited",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [
            {
                "type": "output_text",
                "text": "The game starts at 8.",
                "annotations": [
                    {
                        "type": "url_citation",
                        "start_index": 0,
                        "end_index": 21,
                        "url": "https://example.com/schedule",
                        "title": "Schedule",
                    }
                ],
            }
        ],
    }
    adapter = install_api(monkeypatch, "openai", [response_payload("openai", [output])], [])
    result = asyncio.run(
        adapter.generate_response(
            [{"role": "user", "content": "Game time?"}],
            context="",
            max_tokens=2048,
            tools=[],
            allow_web=True,
        )
    )
    assert result == "The game starts at 8. (https://example.com/schedule)"


def test_openai_incomplete_response_does_not_execute_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    execute = AsyncMock()
    adapter = install_api(
        monkeypatch,
        "openai",
        [
            response_payload(
                "openai",
                [
                    tool_call("openai", "query_database", {"sql": "SELECT 1"}, "call_query"),
                ],
                status="incomplete",
            )
        ],
        [],
    )
    with pytest.raises(ValueError):
        asyncio.run(
            adapter.generate_response(
                [],
                context="",
                max_tokens=2048,
                tools=[AITool(DB_QUERY_TOOL, execute)],
                allow_web=False,
            )
        )
    execute.assert_not_awaited()


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_tool_turn_keeps_latest_text_when_final_turn_is_empty(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    adapter = install_api(
        monkeypatch,
        provider,
        [
            response_payload(
                provider,
                [
                    text_output(provider, "Checking that."),
                    tool_call(provider, "query_database", {"sql": "SELECT 1"}, "call_query"),
                ],
                status="tools",
            ),
            response_payload(provider, []),
        ],
        [],
    )
    execute = AsyncMock(return_value="[]")
    result = asyncio.run(
        adapter.generate_response(
            [],
            context="",
            max_tokens=2048,
            tools=[AITool(DB_QUERY_TOOL, execute)],
            allow_web=False,
        )
    )
    assert result == "Checking that."


def test_openai_malformed_json_is_returned_as_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict[str, object]] = []
    call = tool_call("openai", "query_database", {}, "call_query")
    call["arguments"] = "{broken"
    adapter = install_api(
        monkeypatch,
        "openai",
        [
            response_payload("openai", [call], status="tools"),
            response_payload("openai", [text_output("openai", "Could not query.")]),
        ],
        requests,
    )
    execute = AsyncMock()
    asyncio.run(
        adapter.generate_response(
            [],
            context="",
            max_tokens=2048,
            tools=[AITool(DB_QUERY_TOOL, execute)],
            allow_web=False,
        )
    )
    execute.assert_not_awaited()
    assert requests[1]["input"][-1]["call_id"] == "call_query"
    assert requests[1]["input"][-1]["output"].startswith("Error:")
