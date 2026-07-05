from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol
from triage_copilot.explanation.explanation_generator import is_grounded


def test_is_grounded_uses_collected_facts():
    facts = ExtractedFacts(
        symptom_category="chest_pain",
        duration_minutes=30,
        severity="mild",
        associated_symptoms=["shortness_of_breath"],
        explicit_negatives=["fever"],
        history_flags=[],
        raw_text="chest pain",
    )

    assert is_grounded("The patient reports chest pain and shortness of breath.", facts, None)
    assert not is_grounded("The patient reports dizziness.", facts, None)
