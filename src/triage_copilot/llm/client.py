from __future__ import annotations

import time
from typing import Type

from openai import APIError, OpenAI
from pydantic import BaseModel, ValidationError

from triage_copilot.config import ModelRegistry, settings
from triage_copilot.logging import get_logger


logger = get_logger(__name__)


class ExtractionFailedError(RuntimeError):
    """Raised when all configured providers fail for a task."""


class LLMClient:
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry

    async def complete(self, task: str, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        config = self.model_registry.get_model_config(task)
        attempts = [config.primary, config.fallback]

        for attempt_config in attempts:
            if attempt_config is None:
                continue

            client = OpenAI(
                base_url=attempt_config.base_url,
                api_key=attempt_config.api_key,
            )

            for retry in range(settings.LLM_MAX_RETRIES):
                try:
                    response = await client.chat.completions.create(
                        model=attempt_config.model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
                    )
                    content = response.choices[0].message.content
                    if content is None:
                        raise ValidationError.from_exception_data(
                            title="response_content",
                            line_errors=[],
                        )
                    return response_model.model_validate_json(content)
                except (ValidationError, APIError, TimeoutError) as exc:
                    logger.warning(
                        "llm_call_failed task=%s provider=%s attempt=%s error=%s",
                        task,
                        attempt_config.provider,
                        retry,
                        str(exc),
                    )
                    time.sleep(settings.LLM_RETRY_BACKOFF_SECONDS * (retry + 1))

        raise ExtractionFailedError(f"All providers exhausted for task={task}")


__all__ = ["LLMClient", "ExtractionFailedError"]
