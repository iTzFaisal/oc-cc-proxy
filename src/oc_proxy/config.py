from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4000
OPENCODE_GO_API_BASE = "https://opencode.ai/zen/go/v1"
OPENCODE_GO_API_KEY_ENV = "OPENCODE_GO_API_KEY"


class ConfigurationError(RuntimeError):
    """Raised when required proxy configuration is missing or invalid."""


@dataclass(frozen=True)
class ProxySettings:
    api_key: str
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    api_base: str = OPENCODE_GO_API_BASE
    debug: bool = False


def load_settings(*, env_file: str | None = None, api_key: str | None = None, debug: bool = False) -> ProxySettings:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    resolved_api_key = api_key or os.getenv(OPENCODE_GO_API_KEY_ENV)
    if not resolved_api_key:
        raise ConfigurationError(
            f"Missing OpenCode Go API key. Pass --api-key or set {OPENCODE_GO_API_KEY_ENV} in the environment or a .env file before starting oc-cc-proxy."
        )

    host = os.getenv("OC_PROXY_HOST", DEFAULT_HOST)
    port_value = os.getenv("OC_PROXY_PORT", str(DEFAULT_PORT))
    try:
        port = int(port_value)
    except ValueError as exc:
        raise ConfigurationError(f"OC_PROXY_PORT must be an integer, got {port_value!r}.") from exc

    return ProxySettings(api_key=resolved_api_key, host=host, port=port, debug=debug)


def build_litellm_config(settings: ProxySettings) -> dict[str, Any]:
    config: dict[str, Any] = {
        "model_list": [
            {
                "model_name": "*",
                "litellm_params": {
                    "model": "openai/*",
                    "api_base": settings.api_base,
                    "api_key": settings.api_key,
                },
            }
        ],
        "litellm_settings": {
            "callbacks": ["oc_proxy.reasoning.deepseek_reasoning_content_callback"],
            "drop_params": True,
            "set_verbose": settings.debug,
            "use_chat_completions_url_for_anthropic_messages": True,
        },
    }
    return config


def write_litellm_config(settings: ProxySettings, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    callback_dir = path.parent / "oc_proxy"
    callback_dir.mkdir(exist_ok=True)
    (callback_dir / "__init__.py").write_text("", encoding="utf-8")
    shutil.copyfile(Path(__file__).with_name("reasoning.py"), callback_dir / "reasoning.py")
    with path.open("w", encoding="utf-8") as config_file:
        yaml.safe_dump(build_litellm_config(settings), config_file, sort_keys=False)
    return path


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    sensitive = {"authorization", "x-api-key", "api-key"}
    return {key: ("<redacted>" if key.lower() in sensitive else value) for key, value in headers.items()}


def summarize_payload_shape(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: summarize_payload_shape(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [summarize_payload_shape(payload[0])] if payload else []
    return type(payload).__name__
