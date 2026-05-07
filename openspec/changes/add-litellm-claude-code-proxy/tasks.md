## 1. Project Setup

- [x] 1.1 Add LiteLLM and required runtime dependencies using `uv`.
- [x] 1.2 Add a Python package/module structure for the local proxy wrapper.
- [x] 1.3 Add a runnable CLI entry point for starting the proxy locally.

## 2. LiteLLM Proxy Configuration

- [x] 2.1 Add LiteLLM configuration generation or static config for OpenCode Go.
- [x] 2.2 Configure wildcard model routing with `model_name: "*"` and `model: "openai/*"`.
- [x] 2.3 Configure OpenCode Go API base as `https://opencode.ai/zen/go/v1`.
- [x] 2.4 Read the OpenCode Go API key from environment configuration and fail clearly when missing.
- [x] 2.5 Ensure the local proxy listens on the documented default host and port for Claude Code.

## 3. Claude Code Compatibility

- [x] 3.1 Verify the proxy accepts Anthropic Messages API requests without requiring a real Anthropic API key.
- [x] 3.2 Verify non-streaming Messages API requests return Anthropic-shaped responses.
- [x] 3.3 Verify Claude Code model names pass through dynamically to OpenCode Go.
- [x] 3.4 Verify streaming Messages API requests return valid Anthropic-compatible stream events.
- [x] 3.5 Verify stream completion sends a terminal event that Claude Code can consume.

## 4. Tool-Use Validation

- [x] 4.1 Add a validation request that sends Anthropic tool definitions through the proxy.
- [x] 4.2 Verify upstream requests include equivalent OpenAI-compatible tools.
- [x] 4.3 Verify upstream tool calls return to the client as Anthropic `tool_use` blocks.
- [x] 4.4 Verify follow-up `tool_result` messages translate into a valid next upstream model turn.
- [x] 4.5 Verify streamed tool-call behavior preserves tool name, input, and identifier information.
- [x] 4.6 Document any tool-use incompatibility as blocking before marking Claude Code support as ready.

## 5. Observability and Debugging

- [x] 5.1 Add a debug mode for inspecting relevant request and response metadata.
- [x] 5.2 Ensure debug output avoids printing API keys or sensitive authorization headers.
- [x] 5.3 Capture enough payload-shape information to diagnose tool and streaming translation failures.

## 6. Documentation

- [x] 6.1 Add setup instructions for installing and running the Python-first proxy with `uv`.
- [x] 6.2 Add an `.env` example documenting the OpenCode Go API key variable.
- [x] 6.3 Add Claude Code user-scope `settings.json` example with wildcard model passthrough.
- [x] 6.4 Document known-good validation commands and expected outcomes.
- [x] 6.5 Document current limitations, including unsupported Anthropic-specific features if discovered.

## 7. Verification

- [x] 7.1 Run project tests or validation scripts for text, streaming, wildcard routing, and tools.
- [x] 7.2 Run formatting or linting commands introduced by this change.
- [x] 7.3 Confirm OpenSpec status shows the change ready for apply completion.
