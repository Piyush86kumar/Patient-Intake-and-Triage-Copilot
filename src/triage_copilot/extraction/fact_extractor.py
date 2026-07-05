from __future__ import annotations

from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.extraction.prompts import build_extraction_prompt
from triage_copilot.llm.client import LLMClient
from triage_copilot.config import model_registry


llm_client = LLMClient(model_registry)


async def extract_facts(raw_text: str, prior_facts: ExtractedFacts | None = None) -> ExtractedFacts:
    prompt = build_extraction_prompt(raw_text, prior_facts)
    return await llm_client.complete("fact_extraction", prompt, ExtractedFacts)


__all__ = ["extract_facts"]
