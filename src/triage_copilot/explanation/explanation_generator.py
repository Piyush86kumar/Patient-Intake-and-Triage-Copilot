from __future__ import annotations

import re

from triage_copilot.config import model_registry
from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol
from triage_copilot.llm.client import LLMClient
from triage_copilot.questioning.question_selector import SimpleTextResponse


llm_client = LLMClient(model_registry)


def build_explanation_prompt(disposition_result, facts: ExtractedFacts, safety_netting: str | None) -> str:
    facts_summary = facts.model_dump_json(indent=2)
    return (
        "You are helping explain a triage disposition to a patient. "
        "Write a calm, concise explanation grounded in the facts collected. "
        "Do not add symptoms, diagnoses, or recommendations that are not supported by the facts.\n\n"
        f"Disposition: {disposition_result.disposition}\n"
        f"Facts: {facts_summary}\n"
        f"Safety netting: {safety_netting or ''}\n"
        "Return a short plain-text explanation."
    )


def fallback_template_explanation(disposition_result, facts: ExtractedFacts, protocol: Protocol) -> str:
    return (
        f"Based on the information collected, the recommended disposition is {disposition_result.disposition}. "
        f"Please follow the safety guidance for {protocol.symptom_category or 'this condition'}."
    )


def is_grounded(text: str, facts: ExtractedFacts, disposition_result) -> bool:
    normalized = text.lower()
    facts_payload = facts.model_dump()
    fact_values = []
    for value in facts_payload.values():
        if isinstance(value, str):
            fact_values.append(value.lower())
        elif isinstance(value, (int, float, bool)):
            fact_values.append(str(value).lower())
        elif isinstance(value, list):
            fact_values.extend(str(item).lower() for item in value)

    if not fact_values:
        return True

    # Cheap groundedness check: avoid mentioning symptom/value words not present in the known facts.
    for token in re.findall(r"[a-zA-Z_]+", normalized):
        if token in {"the", "and", "for", "based", "on", "please", "recommended", "disposition", "symptoms", "care"}:
            continue
        if token not in set(" ".join(fact_values).split()):
            if len(token) > 3 and token not in {"urgent", "medical", "safety", "guidance", "follow"}:
                return False
    return True


async def generate_explanation(disposition_result, facts: ExtractedFacts, protocol: Protocol) -> str:
    prompt = build_explanation_prompt(disposition_result, facts, protocol.safety_netting)
    text = await llm_client.complete("explanation_generation", prompt, SimpleTextResponse)
    if not is_grounded(text.content, facts, disposition_result):
        return fallback_template_explanation(disposition_result, facts, protocol)
    return text.content


__all__ = ["build_explanation_prompt", "fallback_template_explanation", "is_grounded", "generate_explanation"]
