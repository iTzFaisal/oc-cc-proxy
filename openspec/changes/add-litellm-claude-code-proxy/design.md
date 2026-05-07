## Context

The repository is currently a minimal Python project with OpenSpec scaffolding and no application implementation. The target integration is Claude Code on a user's machine, configured with `ANTHROPIC_BASE_URL=http://localhost:4000`, talking to a local proxy that forwards requests to OpenCode Go's OpenAI-compatible endpoint at `https://opencode.ai/zen/go/v1/chat/completions`.

Claude Code's core coding workflow depends on Anthropic Messages API semantics, including streaming and tool use. OpenCode Go exposes OpenAI chat completions semantics. LiteLLM Proxy is a strong first translation layer because it can expose Anthropic-compatible `/v1/messages` while routing to OpenAI-compatible backends.

## Goals / Non-Goals

**Goals:**
- Provide a Python-first local wrapper that runs LiteLLM Proxy for Claude Code users.
- Use wildcard model routing so the model names configured in Claude Code user-scope `settings.json` pass through to OpenCode Go without maintaining explicit aliases.
- Use API-key-only authentication for OpenCode Go.
- Support streaming responses because Claude Code's interactive UX depends on incremental output.
- Treat Claude Code tool compatibility as required, including tool definitions, tool calls, tool results, and streamed tool-call chunks.
- Provide clear setup and validation documentation so others can reproduce the proxy locally.

**Non-Goals:**
- Do not implement a full custom Anthropic-to-OpenAI protocol proxy unless LiteLLM proves insufficient.
- Do not restrict wildcard routing to a known model allowlist in the initial design.
- Do not add Docker packaging in the first implementation pass.
- Do not manage or acquire OpenCode Go subscriptions or credentials.
- Do not claim compatibility with all Anthropic-only features such as prompt caching or extended thinking unless validated.

## Decisions

### Use LiteLLM Proxy as the Translation Layer

LiteLLM Proxy will be the initial protocol bridge between Claude Code and OpenCode Go. It already supports Anthropic-style `/v1/messages` inputs and OpenAI-compatible upstream providers, which avoids building a custom translation layer before there is evidence it is needed.

Alternative considered: write a custom FastAPI proxy from the start. This gives maximum control over streaming and tool-call translation but duplicates difficult protocol behavior prematurely.

### Use Wildcard Model Passthrough

The LiteLLM configuration will use `model_name: "*"` and `model: "openai/*"`. Claude Code remains the source of truth for model selection through settings such as `ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro`, and LiteLLM forwards the requested model name to OpenCode Go.

Alternative considered: define explicit model aliases for Haiku, Sonnet, and Opus. This is safer but would require config edits whenever users change Claude Code settings.

### Build Python-First Before Docker

The first implementation will use Python project tooling and `uv` to run the proxy locally. This keeps debugging simple while validating the uncertain parts of the integration, especially Claude Code tools and streaming behavior.

Alternative considered: Docker-first packaging. This is better for distribution but adds packaging friction before the protocol behavior is proven.

### Make Tool Compatibility a Validation Gate

Tool use is core to Claude Code. The implementation must verify that Anthropic tool definitions become OpenAI tools upstream, OpenAI tool calls become Anthropic `tool_use` blocks downstream, and Claude Code can send `tool_result` blocks back through the proxy for follow-up model calls.

Alternative considered: ship text and streaming first, then treat tools as a later enhancement. This would not satisfy the main Claude Code use case.

### Prefer Observability Over Early Reimplementation

If tool or streaming behavior fails, the next step should be adding debug visibility around request and response shapes before replacing LiteLLM. This should make failures concrete: dropped fields, malformed tool arguments, mismatched IDs, unsupported parameters, or stream-event mismatches.

Alternative considered: immediately build custom compatibility patches. This risks solving the wrong problem before seeing actual failure modes.

## Risks / Trade-offs

- LiteLLM wildcard routing may not behave identically on Anthropic `/v1/messages` and OpenAI `/chat/completions` routes -> Validate with real `/v1/messages` requests using dynamic model names.
- OpenCode Go may not support OpenAI tool calls fully -> Add explicit tool-call validation before considering the proxy usable for Claude Code.
- Streaming tool-call chunks may be malformed or lossy across translation -> Include streamed tool-use scenarios in validation, not only non-streaming calls.
- Claude Code may send Anthropic-specific fields that OpenCode Go or LiteLLM does not support -> Inspect and document unsupported parameters; strip or adapt only if a concrete failure is observed.
- Wildcard routing forwards invalid model names to OpenCode Go -> Accept this in the initial design because Claude Code settings are intentionally the source of truth.
- LiteLLM may not provide enough visibility into transformed payloads -> Add debug logging or callbacks if required before moving to a custom proxy.

## Migration Plan

This is a new local development utility, so there is no existing production migration. Users can roll back by restoring Claude Code's original Anthropic environment variables or stopping the local proxy.

## Open Questions

- Which exact OpenCode Go model names should be recommended in documentation as known-good examples?
- Does OpenCode Go return OpenAI-compatible tool calls for the target models, or do some models ignore tool definitions?
- Does Claude Code require any additional Anthropic endpoints beyond `/v1/messages` for normal local coding sessions?
