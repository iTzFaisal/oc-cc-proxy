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


def test_callback_strips_thinking_blocks_for_other_models() -> None:
    callback = DeepSeekReasoningContentCallback()
    kwargs = {"model": "qwen3.6-plus", "messages": [{"role": "assistant", "thinking_blocks": []}]}

    result = __import__("asyncio").run(callback.async_pre_call_deployment_hook(kwargs, CallTypes.acompletion))

    assert "thinking_blocks" not in result["messages"][0]
    assert "reasoning_content" not in result["messages"][0]


def test_kimi_callback_preserves_reasoning_content() -> None:
    callback = DeepSeekReasoningContentCallback()
    kwargs = {
        "model": "kimi-k2.5",
        "messages": [
            {
                "role": "assistant",
                "thinking_blocks": [{"type": "thinking", "thinking": "reasoning"}],
                "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_status", "arguments": "{}"}}],
            }
        ],
    }

    result = __import__("asyncio").run(callback.async_pre_call_deployment_hook(kwargs, CallTypes.acompletion))
    message = result["messages"][0]

    assert message["reasoning_content"] == "reasoning"
    assert "thinking_blocks" not in message


def test_minimax_streaming_callback_skips_empty_choices() -> None:
    async def collect() -> list[object]:
        callback = DeepSeekReasoningContentCallback()

        async def stream():
            yield type("Chunk", (), {"choices": []})()
            yield type("Chunk", (), {"choices": [object()]})()

        return [
            item
            async for item in callback.async_post_call_streaming_iterator_hook(
                None, stream(), {"model": "minimax-m2.7"}
            )
        ]

    result = __import__("asyncio").run(collect())

    assert len(result) == 1


def test_litellm_empty_choices_patch_is_installed() -> None:
    from litellm.llms.anthropic.experimental_pass_through.adapters.streaming_iterator import AnthropicStreamWrapper

    chunk = type("Chunk", (), {"choices": []})()

    assert AnthropicStreamWrapper(None, "minimax-m2.7")._should_start_new_content_block(chunk) is False


def test_litellm_repetition_patch_ignores_empty_choices() -> None:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper

    chunk = type("Chunk", (), {"choices": []})()
    logging_obj = type("Logging", (), {"model_call_details": {}})()
    wrapper = CustomStreamWrapper(completion_stream=None, model="minimax-m2.7", logging_obj=logging_obj)
    wrapper.chunks = [chunk, chunk]

    wrapper.raise_on_model_repetition()

    assert wrapper._repeated_messages_count == 1
