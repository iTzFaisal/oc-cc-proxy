from __future__ import annotations

from typing import Any

from litellm.integrations.custom_logger import CustomLogger
from litellm.types.utils import CallTypes


class DeepSeekReasoningContentCallback(CustomLogger):
    """Preserve DeepSeek reasoning metadata across tool-result turns."""

    async def async_pre_call_deployment_hook(self, kwargs: dict[str, Any], call_type: CallTypes | None) -> dict[str, Any]:
        if call_type not in {CallTypes.completion, CallTypes.acompletion}:
            return kwargs

        model = str(kwargs.get("model") or "")
        if not model.startswith("deepseek-v4"):
            return kwargs

        messages = kwargs.get("messages")
        if not isinstance(messages, list):
            return kwargs

        for message in messages:
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            thinking_blocks = message.pop("thinking_blocks", None)
            reasoning_content = _thinking_blocks_to_reasoning_content(thinking_blocks)
            if reasoning_content:
                message["reasoning_content"] = reasoning_content
            if message.get("tool_calls") and message.get("content") is None:
                message["content"] = ""
        return kwargs


def _thinking_blocks_to_reasoning_content(thinking_blocks: Any) -> str | None:
    if not isinstance(thinking_blocks, list):
        return None

    parts: list[str] = []
    for block in thinking_blocks:
        if isinstance(block, dict) and block.get("type") == "thinking" and block.get("thinking"):
            parts.append(str(block["thinking"]))
    return "\n".join(parts) or None


deepseek_reasoning_content_callback = DeepSeekReasoningContentCallback()
