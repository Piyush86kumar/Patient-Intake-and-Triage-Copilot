from __future__ import annotations

from pydantic import BaseModel

from triage_copilot.config import model_registry
from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol
from triage_copilot.llm.client import LLMClient


class SimpleTextResponse(BaseModel):
    content: str


llm_client = LLMClient(model_registry)


def next_missing_field(facts: ExtractedFacts, protocol: Protocol) -> str | None:
    """Return the first required field that is not yet present or non-null in the facts."""

    payload = facts.model_dump()
    for field in protocol.required_fields:
        value = payload.get(field, getattr(facts, field, None))
        if value in (None, "", [], {}):
            return field

    return None


async def phrase_question(field: str, protocol: Protocol) -> str:
    prompt = (
        f'Phrase this as a natural, calm follow-up question: {field}\n'
        'Return JSON with a single key "content" containing the question.'
    )
    response = await llm_client.complete("question_phrasing", prompt, SimpleTextResponse)
    return response.content


__all__ = ["SimpleTextResponse", "next_missing_field", "phrase_question"]
