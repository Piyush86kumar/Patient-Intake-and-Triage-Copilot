from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = Path(os.getenv("TRIAGE_COPILOT_ENV_FILE", BASE_DIR / ".env"))
MODELS_FILE = BASE_DIR / "models.yaml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    NVIDIA_NIM_BASE_URL: str = Field(..., description="Base URL for NVIDIA NIM")
    NVIDIA_NIM_API_KEY: str = Field(..., description="API key for NVIDIA NIM")
    GOOGLE_AI_STUDIO_BASE_URL: str = Field(..., description="Base URL for Google AI Studio")
    GOOGLE_AI_STUDIO_API_KEY: str = Field(..., description="API key for Google AI Studio")
    OPENROUTER_BASE_URL: str = Field(..., description="Base URL for OpenRouter")
    OPENROUTER_API_KEY: str = Field(..., description="API key for OpenRouter")

    LLM_REQUEST_TIMEOUT_SECONDS: int = Field(15, ge=1)
    LLM_MAX_RETRIES: int = Field(2, ge=0)
    LLM_RETRY_BACKOFF_SECONDS: int = Field(1, ge=0)

    APP_ENV: str = Field("development")
    APP_HOST: str = Field("0.0.0.0")
    APP_PORT: int = Field(8000, ge=1, le=65535)
    APP_LOG_LEVEL: str = Field("INFO")

    DATABASE_URL: str = Field("sqlite:///./data/triage.db")
    MAX_QUESTIONS_PER_CONVERSATION: int = Field(8, ge=1)
    CONVERSATION_TIMEOUT_SECONDS: int = Field(600, ge=1)
    API_KEY: str = Field("changeme_local_dev_key")
    SYNTHETIC_DATA_ONLY: bool = Field(True)


class ProviderConfig(BaseModel):
    provider: str
    model: str
    base_url: str
    api_key: str


class ProviderModelConfig(BaseModel):
    primary: ProviderConfig | None = None
    fallback: ProviderConfig | None = None


class ModelRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._config = self._load_models()

    def _load_models(self) -> dict[str, ProviderModelConfig]:
        if not MODELS_FILE.exists():
            raise RuntimeError(f"Model definition file not found: {MODELS_FILE}")

        with MODELS_FILE.open("r", encoding="utf-8") as handle:
            raw_config = yaml.safe_load(handle) or {}

        providers = raw_config.get("providers", {})
        tasks = raw_config.get("tasks", {})
        if not isinstance(providers, dict) or not isinstance(tasks, dict):
            raise RuntimeError("models.yaml must define 'providers' and 'tasks' mappings")

        resolved: dict[str, ProviderModelConfig] = {}
        for task_name, task_config in tasks.items():
            if not isinstance(task_config, dict):
                raise RuntimeError(f"Task '{task_name}' in models.yaml must be a mapping")

            resolved[task_name] = self._resolve_task(task_name, task_config, providers)

        return resolved

    def _resolve_task(
        self,
        task_name: str,
        task_config: dict[str, Any],
        providers: dict[str, dict[str, str]],
    ) -> ProviderModelConfig:
        resolved_entries: dict[str, ProviderConfig | None] = {}
        for role in ("primary", "fallback"):
            entry = task_config.get(role)
            if entry is None:
                resolved_entries[role] = None
                continue
            if not isinstance(entry, dict):
                raise RuntimeError(f"Task '{task_name}' entry '{role}' must be a mapping")

            provider_name = entry.get("provider")
            model_name = entry.get("model")
            if not provider_name or not model_name:
                raise RuntimeError(f"Task '{task_name}' entry '{role}' is missing provider/model")

            provider_config = providers.get(provider_name)
            if not isinstance(provider_config, dict):
                raise RuntimeError(f"Provider '{provider_name}' referenced by task '{task_name}' is undefined")

            base_url_env = provider_config.get("base_url_env")
            api_key_env = provider_config.get("api_key_env")
            if not isinstance(base_url_env, str) or not isinstance(api_key_env, str):
                raise RuntimeError(f"Provider '{provider_name}' in models.yaml is missing env references")

            try:
                base_url = getattr(self.settings, base_url_env)
                api_key = getattr(self.settings, api_key_env)
            except AttributeError as exc:
                raise RuntimeError(
                    f"Missing required settings for provider '{provider_name}': {base_url_env} or {api_key_env}"
                ) from exc

            resolved_entries[role] = ProviderConfig(
                provider=provider_name,
                model=model_name,
                base_url=base_url,
                api_key=api_key,
            )

        return ProviderModelConfig(**resolved_entries)

    def get_model_config(self, task: str) -> ProviderModelConfig:
        try:
            return self._config[task]
        except KeyError as exc:
            raise KeyError(f"Unknown task '{task}'") from exc


def _build_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:  # pragma: no cover - import-time guard for clearer failure.
        raise RuntimeError(f"Missing required settings: {exc}") from exc


settings = _build_settings()
model_registry = ModelRegistry(settings=settings)

__all__ = [
    "Settings",
    "ProviderConfig",
    "ProviderModelConfig",
    "ModelRegistry",
    "settings",
    "model_registry",
]
