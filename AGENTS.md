# Agent Notes

- This repo is a Python `>=3.12` project for `oc-cc-proxy`, a local LiteLLM-based Claude Code proxy for OpenCode Go.
- Always use `uv` for Python environment and dependency management. Prefer `uv sync`, `uv add ...`, `uv remove ...`, and `uv run ...`; do not use raw `pip`, `python -m venv`, or manual virtualenv management.
- `.python-version` pins local development to Python `3.12`; keep new Python work compatible with that baseline.
- The source package lives under `src/oc_proxy/`. CLI entry points are `uv run oc-cc-proxy` for the proxy and `uv run oc-cc-proxy-validate` for live compatibility validation.
- Runtime dependencies include `litellm[proxy]`, `python-dotenv`, `pyyaml`, and `httpx`. Dev checks use `pytest` and `ruff`.
- Standard local verification commands are `uv run pytest` and `uv run ruff check .`. Live validation requires a configured `.env` with `OPENCODE_GO_API_KEY` and a running proxy, then `uv run oc-cc-proxy-validate --model deepseek-v4-pro`.
- The proxy generates LiteLLM config dynamically with wildcard routing: `model_name: "*"`, `model: "openai/*"`, and `api_base: "https://opencode.ai/zen/go/v1"`. It also sets `use_chat_completions_url_for_anthropic_messages: true` because OpenCode Go exposes `/chat/completions`, not OpenAI `/responses`.
- Do not add a LiteLLM `master_key` unless requirements change. Claude Code should only need a non-empty local `ANTHROPIC_API_KEY`; upstream auth comes from `OPENCODE_GO_API_KEY`.
- DeepSeek V4 tool-result turns require preserving reasoning metadata. `src/oc_proxy/reasoning.py` provides a LiteLLM callback that converts returned Anthropic `thinking` blocks back into upstream `reasoning_content` before follow-up tool-result requests. Keep this callback wired into generated config and copied beside temporary config files, because LiteLLM loads custom callbacks relative to the config file path.
- Validation should replay the actual prior assistant content when testing `tool_result` follow-up turns. Synthetic assistant `tool_use` messages can omit required reasoning metadata and produce false failures with `deepseek-v4-pro`.
- `.gitignore` only ignores `.venv/`; update it deliberately if new generated files, caches, build artifacts, or lockfiles should be excluded.
- OpenSpec scaffolding is present under `openspec/`, with repo-local OpenCode slash commands in `.opencode/commands/opsx-*.md` and skills in `.opencode/skills/`. Use `/opsx-propose`, `/opsx-apply`, `/opsx-explore`, and `/opsx-archive` for OpenSpec-managed changes instead of ad hoc proposal/task workflows.
