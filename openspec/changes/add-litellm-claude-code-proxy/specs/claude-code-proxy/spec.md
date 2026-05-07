## ADDED Requirements

### Requirement: Local Anthropic Messages endpoint
The system SHALL expose a local Anthropic Messages-compatible endpoint suitable for Claude Code when `ANTHROPIC_BASE_URL` points to the proxy.

#### Scenario: Claude Code sends a Messages API request
- **WHEN** a client sends an Anthropic Messages API request to the local proxy
- **THEN** the proxy accepts the request without requiring a real Anthropic API key

#### Scenario: Claude Code receives an Anthropic-shaped response
- **WHEN** OpenCode Go returns a successful OpenAI-compatible response through the proxy
- **THEN** the client receives a response shaped as an Anthropic Messages API response

### Requirement: OpenCode Go upstream routing
The system SHALL route model requests to OpenCode Go's OpenAI-compatible chat completions API using API-key-only authentication.

#### Scenario: Proxy forwards to OpenCode Go
- **WHEN** the proxy receives a valid Messages API request
- **THEN** it forwards the translated request to `https://opencode.ai/zen/go/v1/chat/completions`

#### Scenario: Missing upstream API key
- **WHEN** the proxy starts without the required OpenCode Go API key configuration
- **THEN** it fails with a clear configuration error before accepting requests

### Requirement: Wildcard model passthrough
The system SHALL pass through the model name supplied by Claude Code settings to OpenCode Go without requiring explicit per-model aliases.

#### Scenario: Claude Code uses configured Sonnet model
- **WHEN** Claude Code sends a request with model `deepseek-v4-pro`
- **THEN** the upstream OpenAI-compatible request uses model `deepseek-v4-pro`

#### Scenario: Claude Code uses an arbitrary configured model
- **WHEN** Claude Code sends a request with any model name from user-scope settings
- **THEN** the proxy attempts to route that same model name to OpenCode Go

### Requirement: Streaming response support
The system SHALL support streaming responses from Claude Code through the proxy to OpenCode Go and back.

#### Scenario: Claude Code requests streaming
- **WHEN** a Messages API request includes streaming enabled
- **THEN** the proxy returns Anthropic-compatible streaming events to the client

#### Scenario: Upstream stream completes
- **WHEN** OpenCode Go completes a streamed response
- **THEN** the proxy sends a valid terminal streaming event so Claude Code can finish the turn

### Requirement: Claude Code tool-use compatibility
The system SHALL preserve Claude Code tool-use behavior across the Anthropic-to-OpenAI translation boundary.

#### Scenario: Tool definitions are forwarded upstream
- **WHEN** Claude Code sends Anthropic tool definitions with `input_schema`
- **THEN** the upstream request includes equivalent OpenAI-compatible tool definitions

#### Scenario: Upstream returns a tool call
- **WHEN** OpenCode Go returns an OpenAI-compatible tool call
- **THEN** the proxy returns an Anthropic `tool_use` content block that Claude Code can execute

#### Scenario: Claude Code returns tool results
- **WHEN** Claude Code sends a follow-up message containing `tool_result` blocks
- **THEN** the proxy translates the tool results into an upstream-compatible request for the next model turn

#### Scenario: Tool use works with streaming
- **WHEN** a streamed upstream response contains tool-call data
- **THEN** Claude Code receives valid streamed Anthropic tool-use events without losing tool name, input, or identifier information

### Requirement: Shareable Python-first wrapper
The system SHALL provide a Python-first local run path and documentation suitable for users who want to try the proxy before Docker packaging exists.

#### Scenario: User starts the proxy locally
- **WHEN** a user follows the documented Python-first setup with `uv`
- **THEN** the local proxy starts and listens on the documented host and port

#### Scenario: User configures Claude Code
- **WHEN** a user copies the documented Claude Code environment settings into user-scope `settings.json`
- **THEN** Claude Code routes Messages API calls to the local proxy using the configured model names

### Requirement: Compatibility validation
The system SHALL include validation steps for text completion, wildcard model routing, streaming, and Claude Code tool use.

#### Scenario: Validation covers core behavior
- **WHEN** maintainers run the documented validation flow
- **THEN** it verifies non-streaming text, streaming text, wildcard model passthrough, and tool-use round trips

#### Scenario: Tool compatibility fails
- **WHEN** validation shows that tool calls are dropped, malformed, or ignored
- **THEN** the failure is documented as a blocking compatibility issue before the proxy is described as Claude Code-ready
