# oc-cc-proxy

`oc-cc-proxy` runs a local LiteLLM Proxy that lets Claude Code send Anthropic Messages API requests to OpenCode Go's OpenAI-compatible endpoint.

The proxy listens on `http://127.0.0.1:4000` by default and routes all Claude Code model names through LiteLLM wildcard passthrough to `https://opencode.ai/zen/go/v1/chat/completions`.

## Quickstart (uvx)

```bash
export OPENCODE_GO_API_KEY="your-key-here"
uvx oc-cc-proxy
```

The proxy fails before accepting requests if `OPENCODE_GO_API_KEY` is missing.

## Claude Code Settings

Add equivalent environment values to your Claude Code user-scope `settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:4000",
    "ANTHROPIC_API_KEY": "dummy-key-for-claude-code",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro"
  }
}
```

`ANTHROPIC_API_KEY` only needs to be non-empty for the local proxy path. OpenCode Go authentication uses `OPENCODE_GO_API_KEY` on the proxy process.

## Configuration

- `OPENCODE_GO_API_KEY`: required OpenCode Go API key.
- `OC_PROXY_HOST`: optional host override, defaults to `127.0.0.1`.
- `OC_PROXY_PORT`: optional port override, defaults to `4000`.

## Local Development Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Configure the OpenCode Go API key:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set `OPENCODE_GO_API_KEY`.

4. Start the proxy:

   ```bash
   uv run oc-cc-proxy
   ```

## Validation

With the proxy running, validate non-streaming text, wildcard model passthrough, streaming terminal events, tool definitions, tool results, and streamed tool requests:

```bash
uvx oc-cc-proxy-validate --model deepseek-v4-pro
```

Expected successful output starts each check with `ok:`. Any dropped, malformed, or ignored tool-call behavior should be treated as a blocking compatibility issue before describing the proxy as Claude Code-ready.

Project-local checks:

```bash
uv run pytest
uv run ruff check .
```

## Debugging

Enable LiteLLM verbose logging and local request-shape diagnostics:

```bash
uvx oc-cc-proxy --debug
```

Debug helpers redact sensitive headers such as `Authorization`, `x-api-key`, and `api-key`. Avoid pasting raw upstream logs publicly unless you have checked them for secrets.

To inspect the generated LiteLLM config path without starting the server:

```bash
uvx oc-cc-proxy --print-config --config /tmp/oc-cc-proxy-litellm.yaml
```

## Validated Models

These models pass the full `oc-cc-proxy-validate` suite (non-streaming text, wildcard passthrough, streaming terminal events, tool definitions, streamed tool metadata, and tool-result follow-up):

- `glm-5.1`
- `glm-5`
- `kimi-k2.5`
- `kimi-k2.6`
- `deepseek-v4-pro`
- `deepseek-v4-flash`
- `mimo-v2.5`
- `mimo-v2.5-pro`
- `minimax-m2.7`
- `minimax-m2.5`
- `qwen3.6-plus`
- `qwen3.5-plus`

## Current Limitations

- Tool-use compatibility must be validated against a live OpenCode Go account and target model before claiming a model is known-good for Claude Code.
- DeepSeek V4 and Kimi K2.x models require their returned reasoning metadata to be replayed on assistant tool-call history. The proxy installs a LiteLLM callback that converts Anthropic `thinking` blocks back into upstream `reasoning_content` before `tool_result` follow-up turns. Non-reasoning models (Qwen, GLM, MiMo, MiniMax) have `thinking_blocks` stripped unconditionally to avoid upstream rejection.
- MiniMax M2.7 emits empty `choices` chunks during streaming that LiteLLM's stream handler rejects. The proxy monkeypatches LiteLLM's Anthropic streaming adapter and repetition guard at import time to tolerate these chunks.
- Anthropic-specific features such as prompt caching, extended thinking, and any endpoints beyond `/v1/messages` are not claimed as supported unless separately validated.
