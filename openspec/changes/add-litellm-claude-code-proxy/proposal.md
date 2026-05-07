## Why

Claude Code expects the Anthropic Messages API, while OpenCode Go exposes an OpenAI-compatible chat completions endpoint. A local proxy can let users route Claude Code through their OpenCode Go subscription while preserving core Claude Code workflows, especially streaming and tool use.

## What Changes

- Add a Python-first wrapper for running LiteLLM Proxy locally against OpenCode Go.
- Configure LiteLLM to expose Anthropic-compatible `/v1/messages` behavior for Claude Code.
- Route all Claude Code model names dynamically with wildcard model passthrough to OpenCode Go's OpenAI-compatible `/chat/completions` endpoint.
- Support API-key-only authentication to OpenCode Go.
- Validate streaming responses for Claude Code usability.
- Validate Claude Code tool-use round trips, including tool definitions, tool calls, tool results, and streamed tool-call chunks.
- Provide shareable setup documentation and example Claude Code settings for other users.

## Capabilities

### New Capabilities
- `claude-code-proxy`: Local Claude Code compatibility proxy that routes Anthropic Messages API requests to OpenCode Go through LiteLLM with wildcard model passthrough, streaming, and tool-use validation.

### Modified Capabilities

## Impact

- Adds Python dependencies and runnable entry points for a local LiteLLM-based proxy.
- Adds LiteLLM configuration for OpenCode Go using `https://opencode.ai/zen/go/v1` as the OpenAI-compatible base URL.
- Adds documentation for Claude Code user-scope `settings.json` environment variables.
- Adds validation coverage for text, streaming, wildcard model routing, and Claude Code tool compatibility.
