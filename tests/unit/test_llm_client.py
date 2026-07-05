import asyncio

import pytest
from pydantic import BaseModel

from triage_copilot.config import ModelRegistry, Settings
from triage_copilot.llm.client import ExtractionFailedError, LLMClient


class SampleResponse(BaseModel):
    message: str


class StubCompletions:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        if self.payloads:
            payload = self.payloads.pop(0)
            if payload == "raise":
                raise TimeoutError("timeout")
            return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": payload})()})()]})()
        raise TimeoutError("timeout")


class StubClient:
    def __init__(self, payloads):
        self.chat = type("Chat", (), {"completions": StubCompletions(payloads)})()


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setenv("NVIDIA_NIM_BASE_URL", "https://nim.example")
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "nim-key")
    monkeypatch.setenv("GOOGLE_AI_STUDIO_BASE_URL", "https://google.example")
    monkeypatch.setenv("GOOGLE_AI_STUDIO_API_KEY", "google-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.example")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("LLM_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", "127.0.0.1")
    monkeypatch.setenv("APP_PORT", "8000")
    monkeypatch.setenv("APP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/triage.db")
    monkeypatch.setenv("MAX_QUESTIONS_PER_CONVERSATION", "8")
    monkeypatch.setenv("CONVERSATION_TIMEOUT_SECONDS", "600")
    monkeypatch.setenv("API_KEY", "test")
    monkeypatch.setenv("SYNTHETIC_DATA_ONLY", "true")

    return ModelRegistry(settings=Settings())


def test_complete_returns_parsed_model(monkeypatch, registry):
    monkeypatch.setattr("triage_copilot.llm.client.OpenAI", lambda **kwargs: StubClient(['{"message": "ok"}']))

    client = LLMClient(registry)
    result = asyncio.run(client.complete("fact_extraction", "prompt", SampleResponse))

    assert isinstance(result, SampleResponse)
    assert result.message == "ok"


def test_complete_raises_after_all_providers_fail(monkeypatch, registry):
    monkeypatch.setattr("triage_copilot.llm.client.OpenAI", lambda **kwargs: StubClient(['raise']))

    client = LLMClient(registry)
    with pytest.raises(ExtractionFailedError):
        asyncio.run(client.complete("fact_extraction", "prompt", SampleResponse))
