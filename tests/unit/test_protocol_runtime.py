from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.matcher import match_protocol
from triage_copilot.guidance.protocol_store import protocol_store
from triage_copilot.questioning.question_selector import next_missing_field


def test_protocol_store_loads_all_yaml_protocols():
    assert len(protocol_store.get_all_protocols()) == 7


def test_match_protocol_prefers_exact_symptom_category():
    facts = ExtractedFacts(symptom_category="chest_pain", raw_text="chest pain")
    protocol = match_protocol(facts)
    assert protocol.symptom_category == "chest_pain"


def test_match_protocol_falls_back_to_no_match_protocol():
    facts = ExtractedFacts(symptom_category="mystery_symptom", raw_text="unknown")
    protocol = match_protocol(facts)
    assert protocol.protocol_id == "fallback_no_match_v1"


def test_next_missing_field_returns_first_unset_required_field():
    facts = ExtractedFacts(symptom_category="chest_pain", raw_text="chest pain", severity="mild")
    protocol = protocol_store.get_protocol("chest_pain_v1")
    assert next_missing_field(facts, protocol) == "duration_minutes"


def test_next_missing_field_returns_none_when_all_required_fields_present():
    facts = ExtractedFacts(
        symptom_category="chest_pain",
        raw_text="chest pain",
        duration_minutes=30,
        severity="mild",
        associated_symptoms=["shortness_of_breath"],
        explicit_negatives=["sweating"],
        history_flags=["radiating_pain"],
    )
    facts.shortness_of_breath = True
    facts.sweating = False
    facts.radiating_pain = False
    protocol = protocol_store.get_protocol("chest_pain_v1")
    assert next_missing_field(facts, protocol) is None
