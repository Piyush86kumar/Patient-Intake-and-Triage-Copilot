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
        'Return JSON with a single key "content" containing the explanation text.'
    )


_DISPOSITION_LABELS = {
    "EMERGENCY": "This needs emergency care right now — please call 911 or go to the nearest emergency room.",
    "URGENT_CARE": "Based on what you've described, I'd recommend visiting an urgent care center today.",
    "PRIMARY_CARE": "This sounds like something your primary care provider can help with — I'd recommend booking an appointment.",
    "SELF_CARE": "This sounds manageable with self-care at home for now.",
}


def fallback_template_explanation(disposition_result, facts: ExtractedFacts, protocol: Protocol) -> str:
    label = _DISPOSITION_LABELS.get(disposition_result.disposition, "Please seek medical attention.")
    safety = protocol.safety_netting or ""
    if safety:
        return f"{label}\n\n{safety}"
    return label


_GROUNDED_ALLOWLIST = {
    "patient", "reports", "based", "recommended", "disposition", "symptoms",
    "follow", "should", "please", "medical", "urgent", "safety", "guidance",
    "because", "care", "chest", "breath", "shortness", "right", "call",
    "hospital", "nearest", "emergency", "room", "visit", "today", "center",
    "primary", "provider", "book", "appointment", "manageable", "home",
    "seek", "attention", "worsens", "worsening", "spreads", "develop",
    "difficulty", "fainting", "signs", "infection", "fever", "wound",
    "redness", "swelling", "warm", "advised", "evaluation", "condition",
    "recommend", "recommends", "advice", "check", "doctor", "nurse",
    "clinic", "within", "hours", "days", "weeks", "better", "worse",
    "worsened", "improve", "improving", "important", "avoid", "rest",
    "fluids", "over", "counter", "medicine", "medication", "pain",
    "relievers", "monitor", "monitoring", "watch", "carefully",
    "instructions", "provided", "above", "given", "describe", "described",
    "noted", "mention", "mentioned", "report", "reported", "triage",
    "level", "next", "steps", "action", "plan", "need", "needs",
    "could", "would", "should", "might", "may", "will", "can",
    "these", "those", "this", "that", "with", "without", "from",
    "your", "have", "has", "had", "been", "being", "some", "any",
    "more", "most", "much", "many", "each", "every", "both", "all",
    "also", "very", "just", "now", "then", "than", "well", "back",
    "still", "even", "only", "once", "here", "there", "when", "where",
    "what", "which", "who", "how", "why", "while", "after", "before",
    "during", "until", "between", "about", "into", "through", "over",
    "under", "above", "below", "along", "around", "among", "across",
    "other", "another", "such", "like", "than", "then",
}


def is_grounded(text: str, facts: ExtractedFacts, disposition_result) -> bool:
    """Check that the explanation doesn't introduce symptoms not in the facts."""
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

    known_terms = set(" ".join(fact_values).split())
    content_tokens = [token for token in re.findall(r"[a-zA-Z_]+", normalized) if len(token) > 3]

    for token in content_tokens:
        if token in _GROUNDED_ALLOWLIST:
            continue
        if token in known_terms:
            continue
        return False
    return True


async def generate_explanation(disposition_result, facts: ExtractedFacts, protocol: Protocol) -> str:
    prompt = build_explanation_prompt(disposition_result, facts, protocol.safety_netting)
    text = await llm_client.complete("explanation_generation", prompt, SimpleTextResponse)
    if not is_grounded(text.content, facts, disposition_result):
        return fallback_template_explanation(disposition_result, facts, protocol)
    return text.content


__all__ = ["build_explanation_prompt", "fallback_template_explanation", "is_grounded", "generate_explanation"]
