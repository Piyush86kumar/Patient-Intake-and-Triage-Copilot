from __future__ import annotations

import json
from typing import Optional

from triage_copilot.extraction.schema import ExtractedFacts


def build_extraction_prompt(raw_text: str, prior_facts: Optional[ExtractedFacts] = None) -> str:
    prior_section = ""
    if prior_facts is not None:
        prior_section = (
            "\n\nPrevious extracted facts (use these as context but do not infer new diagnoses):\n" +
            json.dumps(prior_facts.model_dump(), indent=2)
        )

    return (
        "You are an expert medical fact extractor. Read the user text below and extract only the requested facts. "
        "Do not infer any diagnosis, condition name, or treatment. Output strictly valid JSON with the exact schema fields."
        f"\n\nUser text:\n{raw_text}\n"
        f"{prior_section}\n\n"
        "Extract the following fields exactly as JSON:\n"
        "- symptom_category: string\n"
        "- duration_minutes: integer or null\n"
        "- severity: string or null\n"
        "- associated_symptoms: list of strings\n"
        "- explicit_negatives: list of strings\n"
        "- history_flags: list of strings\n"
        "- raw_text: the original raw text string\n\n"
        "Guidelines:\n"
        "1. Treat hedged or minimizing language such as 'probably', 'maybe', 'might', 'I think', or 'probably nothing but...' as evidence that the symptom is PRESENT rather than absent. Bias toward capturing weak signals rather than filtering them out.\n"
        "2. Do not invent diagnoses, causes, or recommendations. Extract facts only.\n"
        "3. If a field is not present, use null for scalar values and [] for lists.\n"
        "4. Output only the JSON object and nothing else.\n\n"
        "Example output format:\n"
        "{\n"
        "  \"symptom_category\": \"chest_pain\",\n"
        "  \"duration_minutes\": 30,\n"
        "  \"severity\": \"mild\",\n"
        "  \"associated_symptoms\": [\"shortness_of_breath\"],\n"
        "  \"explicit_negatives\": [\"nausea\"],\n"
        "  \"history_flags\": [\"radiating_pain\"],\n"
        "  \"raw_text\": \"...\"\n"
        "}\n"
    )


__all__ = ["build_extraction_prompt"]
