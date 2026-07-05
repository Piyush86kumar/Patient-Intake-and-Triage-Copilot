from triage_copilot.extraction.prompts import build_extraction_prompt
from triage_copilot.extraction.schema import ExtractedFacts


def test_build_extraction_prompt_includes_all_fields():
    raw_text = "I have had chest pain for maybe 20 minutes and probably nothing serious."
    prompt = build_extraction_prompt(raw_text)

    assert "symptom_category" in prompt
    assert "duration_minutes" in prompt
    assert "associated_symptoms" in prompt
    assert "hedged or minimizing language" in prompt
    assert "Do not infer any diagnosis" in prompt


def test_build_extraction_prompt_includes_prior_facts():
    prior = ExtractedFacts(
        symptom_category="chest_pain",
        duration_minutes=20,
        severity="mild",
        associated_symptoms=["shortness_of_breath"],
        explicit_negatives=[],
        history_flags=[],
        raw_text="chest pain",
    )
    prompt = build_extraction_prompt("Still hurting", prior)

    assert "Previous extracted facts" in prompt
    assert "shortness_of_breath" in prompt
