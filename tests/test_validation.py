from __future__ import annotations

from oc_proxy.validation import messages_payload, tool_result_payload


def test_messages_payload_matches_anthropic_shape() -> None:
    payload = messages_payload(model="deepseek-v4-pro")

    assert payload["model"] == "deepseek-v4-pro"
    assert payload["messages"] == [{"role": "user", "content": "Reply with exactly: ok"}]


def test_tool_payload_uses_anthropic_input_schema() -> None:
    payload = messages_payload(model="deepseek-v4-pro", tools=True)

    tool = payload["tools"][0]

    assert tool["name"] == "get_status"
    assert tool["input_schema"]["type"] == "object"


def test_tool_result_payload_preserves_tool_identifier() -> None:
    assistant_content = [
        {"type": "thinking", "thinking": "reasoning", "signature": None},
        {"type": "tool_use", "id": "toolu_validation", "name": "get_status", "input": {"target": "proxy"}},
    ]
    payload = tool_result_payload(model="deepseek-v4-pro", assistant_content=assistant_content)

    assert payload["messages"][1]["content"] == assistant_content
    result = payload["messages"][-1]["content"][0]

    assert result["type"] == "tool_result"
    assert result["tool_use_id"] == "toolu_validation"
