import importlib
import os
import sys

import pytest


REQUIRED_ENV = {
    "NVIDIA_NIM_BASE_URL": "https://nim.example",
    "NVIDIA_NIM_API_KEY": "nim-key",
    "GOOGLE_AI_STUDIO_BASE_URL": "https://google.example",
    "GOOGLE_AI_STUDIO_API_KEY": "google-key",
    "OPENROUTER_BASE_URL": "https://openrouter.example",
    "OPENROUTER_API_KEY": "openrouter-key",
    "LLM_REQUEST_TIMEOUT_SECONDS": "45",
    "MAX_QUESTIONS_PER_CONVERSATION": "5",
}


def _clear_config_module():
    sys.modules.pop("triage_copilot.config", None)


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for key in REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)
    _clear_config_module()
    yield
    _clear_config_module()


def test_settings_and_registry_resolve_provider_values(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("\n".join(f"{key}={value}" for key, value in REQUIRED_ENV.items()) + "\n", encoding="utf-8")
    monkeypatch.setenv("TRIAGE_COPILOT_ENV_FILE", str(env_file))
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    config = importlib.import_module("triage_copilot.config")

    assert config.settings.LLM_REQUEST_TIMEOUT_SECONDS == 45
    assert config.settings.MAX_QUESTIONS_PER_CONVERSATION == 5

    task_config = config.model_registry.get_model_config("fact_extraction")
    assert task_config.primary.provider == "nvidia_nim"
    assert task_config.primary.base_url == "https://nim.example"
    assert task_config.primary.api_key == "nim-key"
    assert task_config.fallback.provider == "openrouter"
    assert task_config.fallback.base_url == "https://openrouter.example"
    assert task_config.fallback.api_key == "openrouter-key"


def test_missing_required_env_vars_raise_clear_error(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(f"{key}={value}" for key, value in REQUIRED_ENV.items() if key != "NVIDIA_NIM_API_KEY") + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TRIAGE_COPILOT_ENV_FILE", str(env_file))
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    for key, value in REQUIRED_ENV.items():
        if key != "NVIDIA_NIM_API_KEY":
            monkeypatch.setenv(key, value)

    with pytest.raises(RuntimeError, match="Missing required settings") as exc_info:
        importlib.import_module("triage_copilot.config")

    assert "NVIDIA_NIM_API_KEY" in str(exc_info.value)
