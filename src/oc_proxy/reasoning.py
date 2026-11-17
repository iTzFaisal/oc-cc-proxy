from __future__ import annotations

import re
from typing import Any

from litellm.integrations.custom_logger import CustomLogger
from litellm.types.utils import CallTypes


# Claude Code identifies itself with these headers (see the CLI bundle's
# ``X-Claude-Code-Session-Id`` / ``x-app`` constants). LiteLLM only forwards
# ``x-*`` headers when ``forward_client_headers_to_llm_api`` is enabled and it
# never forwards ``User-Agent``, so the upstream otherwise sees the OpenAI
# Python SDK's ``AsyncOpenAI/Python <version>`` user agent instead.
_CLIENT_HEADER_ALLOWLIST = frozenset(
    {
        "user-agent",
        "x-app",
        "x-claude-code-session-id",
        "x-claude-code-agent-id",
        "x-claude-code-parent-agent-id",
        "x-claude-code-prompt-id",
    }
)
_SESSION_HEADER_RE = re.compile(r"^x-.+-session-id$", re.IGNORECASE)
_SESSION_FROM_USER_ID_RE = re.compile(r"_session_([0-9A-Za-z-]{8,})")


class ClientHeaderPassthroughCallback(CustomLogger):
    """Forward Claude Code's client identity and session headers upstream.

    LiteLLM sends OpenAI-compatible requests through the OpenAI Python SDK, which
    labels every request with ``AsyncOpenAI/Python <version>``. Copying the
    original headers onto ``data["headers"]`` makes LiteLLM pass them to the
    provider as ``extra_headers``; those win over the SDK defaults, so the
    upstream sees Claude Code's own ``User-Agent`` and session id.
    """

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: Any,
        call_type: Any,
        **kwargs: Any,
    ) -> Any:
        if not isinstance(data, dict):
            return data

        forwarded: dict[str, str] = {}
        for name, value in _incoming_headers(data).items():
            lowered = name.lower()
            if lowered in _CLIENT_HEADER_ALLOWLIST or _SESSION_HEADER_RE.match(lowered):
                forwarded[_canonical_header_name(lowered)] = str(value)

        if "X-Claude-Code-Session-Id" not in forwarded:
            session_id = _session_id_from_metadata(data)
            if session_id:
                forwarded["X-Claude-Code-Session-Id"] = session_id

        if not forwarded:
            return data

        existing = data.get("headers")
        merged = dict(existing) if isinstance(existing, dict) else {}
        forwarded_lower = {key.lower() for key in forwarded}
        for key in [key for key in merged if str(key).lower() in forwarded_lower]:
            del merged[key]
        merged.update(forwarded)
        data["headers"] = merged
        return data


def _canonical_header_name(lowered_name: str) -> str:
    """Canonicalise a lowercased header name (``user-agent`` -> ``User-Agent``).

    openai-python <3 merges custom headers case-sensitively, so sending a
    lowercased ``user-agent`` would leave the SDK default in place and httpx
    would join both values into ``AsyncOpenAI/Python x, claude-cli/...``.
    """
    return "-".join(part.capitalize() for part in lowered_name.split("-"))


def _incoming_headers(data: dict[str, Any]) -> dict[str, Any]:
    request = data.get("proxy_server_request")
    if not isinstance(request, dict):
        return {}
    headers = request.get("headers")
    if not headers:
        return {}
    return dict(headers)


def _session_id_from_metadata(data: dict[str, Any]) -> str | None:
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        return None
    user_id = metadata.get("user_id")
    if not isinstance(user_id, str):
        return None
    match = _SESSION_FROM_USER_ID_RE.search(user_id)
    return match.group(1) if match else None


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
client_header_passthrough_callback = ClientHeaderPassthroughCallback()
_patch_litellm_empty_stream_choices()
