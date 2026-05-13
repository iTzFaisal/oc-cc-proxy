from __future__ import annotations

import argparse
import json
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

from .config import ConfigurationError, load_settings, summarize_payload_shape, write_litellm_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local LiteLLM proxy for Claude Code and OpenCode Go.")
    parser.add_argument("--env-file", help="Path to a .env file containing OPENCODE_GO_API_KEY.")
    parser.add_argument("--api-key", help="OpenCode Go API key for this run.")
    parser.add_argument("--host", help="Override OC_PROXY_HOST for this run.")
    parser.add_argument("--port", type=int, help="Override OC_PROXY_PORT for this run.")
    parser.add_argument("--config", help="Write LiteLLM config to this path instead of a temporary file.")
    parser.add_argument("--print-config", action="store_true", help="Print generated LiteLLM config path and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable LiteLLM verbose logging and request-shape diagnostics.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(env_file=args.env_file, api_key=args.api_key, debug=args.debug)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.host or args.port:
        settings = settings.__class__(
            api_key=settings.api_key,
            host=args.host or settings.host,
            port=args.port or settings.port,
            api_base=settings.api_base,
            debug=settings.debug,
        )

    if args.config:
        config_path = Path(args.config)
        write_litellm_config(settings, config_path)
        temp_dir = None
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="oc-cc-proxy-")
        config_path = Path(temp_dir.name) / "litellm.yaml"
        write_litellm_config(settings, config_path)

    if args.debug:
        shape = summarize_payload_shape({"model": "deepseek-v4-pro", "messages": [{"role": "user", "content": "..."}], "tools": []})
        print(f"Debug request shape example: {json.dumps(shape, sort_keys=True)}", file=sys.stderr)

    if args.print_config:
        print(config_path)
        if temp_dir:
            temp_dir.cleanup()
        return 0

    litellm_executable = shutil.which("litellm")
    if not litellm_executable:
        print("Configuration error: litellm executable was not found in PATH.", file=sys.stderr)
        return 2

    command = [
        litellm_executable,
        "--config",
        str(config_path),
        "--host",
        settings.host,
        "--port",
        str(settings.port),
    ]
    print(f"Starting oc-cc-proxy on http://{settings.host}:{settings.port}")
    print("Set Claude Code ANTHROPIC_BASE_URL to this URL and use any non-empty ANTHROPIC_API_KEY value.")
    try:
        return subprocess.call(command)
    finally:
        if temp_dir:
            temp_dir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
