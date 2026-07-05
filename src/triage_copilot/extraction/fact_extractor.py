from __future__ import annotations

from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.extraction.prompts import build_extraction_prompt
from triage_copilot.llm.client import ExtractionFailedError, LLMClient
from triage_copilot.config import model_registry


llm_client = LLMClient(model_registry)


def _heuristic_fallback(raw_text: str, prior_facts: ExtractedFacts | None = None) -> ExtractedFacts:
    lower = raw_text.lower()
    category = "chest_pain" if any(token in lower for token in ["chest", "pain", "shortness", "breath", "tight"]) else "general"
    associated_symptoms: list[str] = []
    if "shortness" in lower or "breath" in lower:
        associated_symptoms.append("shortness_of_breath")
    if "sweat" in lower:
        associated_symptoms.append("sweating")
    if "arm" in lower or "jaw" in lower:
        associated_symptoms.append("radiating_pain")

    if prior_facts is not None:
        prior_payload = prior_facts.model_dump()
        if prior_payload.get("symptom_category"):
            category = prior_payload["symptom_category"]
        if prior_payload.get("associated_symptoms"):
            associated_symptoms = list(dict.fromkeys([*prior_payload["associated_symptoms"], *associated_symptoms]))

    return ExtractedFacts(
        symptom_category=category,
        duration_minutes=None,
        severity=None,
        associated_symptoms=associated_symptoms,
        explicit_negatives=[],
        history_flags=[],
        raw_text=raw_text,
    )


async def extract_facts(raw_text: str, prior_facts: ExtractedFacts | None = None) -> ExtractedFacts:
    prompt = build_extraction_prompt(raw_text, prior_facts)
    try:
        return await llm_client.complete("fact_extraction", prompt, ExtractedFacts)
    except ExtractionFailedError:
        return _heuristic_fallback(raw_text, prior_facts)


__all__ = ["extract_facts"]
