from __future__ import annotations

from litellm.types.utils import CallTypes

from oc_proxy.reasoning import DeepSeekReasoningContentCallback


def test_deepseek_callback_preserves_reasoning_content() -> None:
    callback = DeepSeekReasoningContentCallback()
    kwargs = {
        "model": "deepseek-v4-pro",
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "thinking_blocks": [{"type": "thinking", "thinking": "reasoning"}],
                "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_status", "arguments": "{}"}}],
            }
        ],
    }

    result = __import__("asyncio").run(callback.async_pre_call_deployment_hook(kwargs, CallTypes.acompletion))
    message = result["messages"][0]

    assert message["reasoning_content"] == "reasoning"
    assert message["content"] == ""
    assert "thinking_blocks" not in message


def test_deepseek_callback_ignores_other_models() -> None:
    callback = DeepSeekReasoningContentCallback()
    kwargs = {"model": "qwen3.6-plus", "messages": [{"role": "assistant", "thinking_blocks": []}]}

    result = __import__("asyncio").run(callback.async_pre_call_deployment_hook(kwargs, CallTypes.acompletion))

    assert "thinking_blocks" in result["messages"][0]
