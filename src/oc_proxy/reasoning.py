from __future__ import annotations

from typing import Any

from litellm.integrations.custom_logger import CustomLogger
from litellm.types.utils import CallTypes


def _patch_litellm_empty_stream_choices() -> None:
    try:
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
        from litellm.llms.anthropic.experimental_pass_through.adapters.streaming_iterator import (
            AnthropicStreamWrapper,
        )
        from litellm.llms.anthropic.experimental_pass_through.adapters.transformation import (
            LiteLLMAnthropicMessagesAdapter,
        )
    except ImportError:
        return

    original_should_start = AnthropicStreamWrapper._should_start_new_content_block
    original_translate = LiteLLMAnthropicMessagesAdapter.translate_streaming_openai_response_to_anthropic
    original_raise_on_repetition = CustomStreamWrapper.raise_on_model_repetition

    if getattr(original_translate, "_oc_proxy_empty_choices_patch", False):
        return

    def patched_should_start(self: Any, chunk: Any) -> bool:
        if _has_empty_choices(chunk):
            return False
        return original_should_start(self, chunk)

    def patched_translate(self: Any, response: Any, current_content_block_index: int) -> dict[str, Any]:
        if _has_empty_choices(response):
            return {
                "type": "content_block_delta",
                "index": current_content_block_index,
                "delta": {"type": "text_delta", "text": ""},
            }
        return original_translate(self, response, current_content_block_index)

    def patched_raise_on_repetition(self: Any) -> None:
        if len(self.chunks) < 2:
            return
        if _has_empty_choices(self.chunks[-1]) or _has_empty_choices(self.chunks[-2]):
            self._repeated_messages_count = 1
            return
        return original_raise_on_repetition(self)

    patched_translate._oc_proxy_empty_choices_patch = True  # type: ignore[attr-defined]
    CustomStreamWrapper.raise_on_model_repetition = patched_raise_on_repetition
    AnthropicStreamWrapper._should_start_new_content_block = patched_should_start
    LiteLLMAnthropicMessagesAdapter.translate_streaming_openai_response_to_anthropic = patched_translate


class DeepSeekReasoningContentCallback(CustomLogger):
    """Preserve DeepSeek reasoning metadata and drop Anthropic-only replay fields."""

    async def async_pre_call_deployment_hook(self, kwargs: dict[str, Any], call_type: CallTypes | None) -> dict[str, Any]:
        if call_type not in {CallTypes.completion, CallTypes.acompletion}:
            return kwargs

        model = str(kwargs.get("model") or "")
        should_preserve_reasoning = model.startswith(("deepseek-v4", "kimi-k2"))
        messages = kwargs.get("messages")
        if not isinstance(messages, list):
            return kwargs

        for message in messages:
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            thinking_blocks = message.pop("thinking_blocks", None)
            reasoning_content = _thinking_blocks_to_reasoning_content(thinking_blocks) if should_preserve_reasoning else None
            if reasoning_content:
                message["reasoning_content"] = reasoning_content
            if message.get("tool_calls") and message.get("content") is None:
                message["content"] = ""
        return kwargs

    async def async_post_call_streaming_iterator_hook(self, user_api_key_dict: Any, response: Any, request_data: dict) -> Any:
        model = str(request_data.get("model") or "")
        async for item in response:
            if model == "minimax-m2.7" and _has_empty_choices(item):
                continue
            yield item


def _has_empty_choices(item: Any) -> bool:
    choices = getattr(item, "choices", None)
    return isinstance(choices, list) and not choices


def _thinking_blocks_to_reasoning_content(thinking_blocks: Any) -> str | None:
    if not isinstance(thinking_blocks, list):
        return None

    parts: list[str] = []
    for block in thinking_blocks:
        if isinstance(block, dict) and block.get("type") == "thinking" and block.get("thinking"):
            parts.append(str(block["thinking"]))
    return "\n".join(parts) or None


deepseek_reasoning_content_callback = DeepSeekReasoningContentCallback()
_patch_litellm_empty_stream_choices()
