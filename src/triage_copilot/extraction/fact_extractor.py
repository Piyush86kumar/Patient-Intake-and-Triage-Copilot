from __future__ import annotations

import logging
import re

from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.extraction.prompts import build_extraction_prompt
from triage_copilot.llm.client import ExtractionFailedError, LLMClient
from triage_copilot.config import model_registry


logger = logging.getLogger(__name__)
llm_client = LLMClient(model_registry)


_SEVERITY_MAP = {
    "mild": "mild",
    "minor": "mild",
    "slight": "mild",
    "moderate": "moderate",
    "severe": "severe",
    "very strong": "severe",
    "extreme": "severe",
    "crushing": "severe",
    "unbearable": "severe",
    "agonizing": "severe",
    "worst": "severe",
    "intense": "severe",
}

_HISTORY_FLAG_MAP = [
    ("cardiac", ["heart condition", "cardiac", "heart disease", "heart attack", "previous heart", "chd", "cad"]),
    ("hypertension", ["hypertension", "high blood pressure"]),
    ("diabetes", ["diabetes", "diabetic"]),
    ("stroke", ["stroke"]),
    ("afib_arrhythmia", ["afib", "arrhythmia", "pacemaker"]),
    ("cardiac_intervention", ["stent", "bypass", "angina"]),
]


def _parse_duration(text: str) -> int | None:
    m = re.search(r"(\d+)\s*(min|mins|minutes|hour|hours|hr|hrs)", text, re.IGNORECASE)
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2).lower()
    if unit in ("hour", "hours", "hr", "hrs"):
        value *= 60
    return value


def _parse_severity(text: str) -> str | None:
    lower = text.lower()
    for phrase, label in _SEVERITY_MAP.items():
        if phrase in lower:
            return label
    return None


def _parse_history(text: str) -> list[str]:
    lower = text.lower()
    flags: list[str] = []
    for flag_name, keywords in _HISTORY_FLAG_MAP:
        if any(kw in lower for kw in keywords):
            flags.append(flag_name)
    return flags


_SYMPTOM_KEYWORDS: list[tuple[list[str], str]] = [
    (["shortness", "breath", "breathing", "dyspnea"], "shortness_of_breath"),
    (["sweat", "perspire", "diaphoretic"], "sweating"),
    (["arm", "jaw", "shoulder", "back pain"], "radiating_pain"),
    (["chest", "tight", "pressure"], "chest_pain"),
    (["wheeze", "wheezing"], "wheezing"),
    (["dizzy", "dizziness", "lightheaded", "faint", "vertigo"], "dizziness"),
    (["nausea", "vomit", "vomiting", "threw up"], "vomiting"),
    (["bloody stool", "blood in stool", "blood in my stool", "rectal bleeding"], "bloody_stools"),
    (["swallow", "swallowing", "throat"], "difficulty_swallowing"),
    (["swollen gland", "swollen lymph", "lump in neck"], "swollen_glands"),
    (["neck stiff", "stiff neck"], "neck_stiffness"),
    (["vision", "blurr", "double vision", "seeing"], "vision_changes"),
]


def _parse_associated_symptoms(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for keywords, symptom_name in _SYMPTOM_KEYWORDS:
        if any(kw in lower for kw in keywords):
            found.append(symptom_name)
    return found


def _heuristic_fallback(raw_text: str, prior_facts: ExtractedFacts | None = None) -> ExtractedFacts:
    lower = raw_text.lower()
    category = "chest_pain" if any(token in lower for token in ["chest", "pain", "shortness", "breath", "tight"]) else "general"
    associated_symptoms = _parse_associated_symptoms(raw_text)

    if prior_facts is not None:
        prior_payload = prior_facts.model_dump()
        if prior_payload.get("symptom_category"):
            category = prior_payload["symptom_category"]
        if prior_payload.get("associated_symptoms"):
            associated_symptoms = list(dict.fromkeys([*prior_payload["associated_symptoms"], *associated_symptoms]))

    return ExtractedFacts(
        symptom_category=category,
        duration_minutes=_parse_duration(raw_text),
        severity=_parse_severity(raw_text),
        associated_symptoms=associated_symptoms,
        explicit_negatives=[],
        history_flags=_parse_history(raw_text),
        raw_text=raw_text,
    )


async def extract_facts(raw_text: str, prior_facts: ExtractedFacts | None = None) -> ExtractedFacts:
    prompt = build_extraction_prompt(raw_text, prior_facts)
    try:
        return await llm_client.complete("fact_extraction", prompt, ExtractedFacts)
    except ExtractionFailedError:
        logger.warning(
            "LLM extraction failed — using heuristic fallback. raw_text=%r", raw_text[:120],
        )
        return _heuristic_fallback(raw_text, prior_facts)


__all__ = ["extract_facts"]
