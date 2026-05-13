from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from oc_proxy.config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    OPENCODE_GO_API_BASE,
    ConfigurationError,
    ProxySettings,
    build_litellm_config,
    load_settings,
    redact_headers,
    summarize_payload_shape,
    write_litellm_config,
)


def test_load_settings_requires_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="Missing OpenCode Go API key"):
        load_settings(env_file=str(tmp_path / "missing.env"))


def test_load_settings_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-test")
    monkeypatch.delenv("OC_PROXY_HOST", raising=False)
    monkeypatch.delenv("OC_PROXY_PORT", raising=False)

    settings = load_settings()

    assert settings.api_key == "sk-test"
    assert settings.host == DEFAULT_HOST
    assert settings.port == DEFAULT_PORT


def test_load_settings_uses_explicit_api_key_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)

    settings = load_settings(api_key="sk-cli")

    assert settings.api_key == "sk-cli"


def test_load_settings_prefers_explicit_api_key_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-env")

    settings = load_settings(api_key="sk-cli")

    assert settings.api_key == "sk-cli"


def test_litellm_config_uses_wildcard_openai_route() -> None:
    config = build_litellm_config(ProxySettings(api_key="sk-test"))

    route = config["model_list"][0]
    assert route["model_name"] == "*"
    assert route["litellm_params"]["model"] == "openai/*"
    assert route["litellm_params"]["api_base"] == OPENCODE_GO_API_BASE
    assert route["litellm_params"]["api_key"] == "sk-test"
    assert config["litellm_settings"]["callbacks"] == ["oc_proxy.reasoning.deepseek_reasoning_content_callback"]
    assert config["litellm_settings"]["use_chat_completions_url_for_anthropic_messages"] is True
    assert "general_settings" not in config


def test_write_litellm_config_round_trips_yaml(tmp_path: Path) -> None:
    path = write_litellm_config(ProxySettings(api_key="sk-test"), tmp_path / "litellm.yaml")

    config = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert config["model_list"][0]["model_name"] == "*"
    assert (tmp_path / "oc_proxy" / "reasoning.py").exists()


def test_redact_headers_removes_sensitive_values() -> None:
    assert redact_headers({"Authorization": "Bearer secret", "Content-Type": "application/json"}) == {
        "Authorization": "<redacted>",
        "Content-Type": "application/json",
    }


def test_summarize_payload_shape_preserves_debug_shape_without_values() -> None:
    shape = summarize_payload_shape({"model": "deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}]})

    assert shape == {"model": "str", "messages": [{"role": "str", "content": "str"}]}
