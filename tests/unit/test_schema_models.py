from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Condition, Protocol, evaluate


def test_recursive_condition_evaluation_supports_composites():
    condition = Condition.model_validate(
        {
            "all": [
                {"field": "duration_minutes", "op": "<", "value": 60},
                {
                    "any": [
                        {"field": "shortness_of_breath", "op": "==", "value": True},
                        {"field": "sweating", "op": "==", "value": True},
                    ],
                },
            ]
        }
    )

    assert evaluate(condition, {"duration_minutes": 30, "shortness_of_breath": True, "sweating": False}) is True
    assert evaluate(condition, {"duration_minutes": 90, "shortness_of_breath": False, "sweating": True}) is False


def test_protocol_model_matches_chest_pain_shape():
    protocol = Protocol.model_validate(
        {
            "protocol_id": "chest_pain_v1",
            "symptom_category": "chest_pain",
            "required_fields": ["duration_minutes", "severity"],
            "red_flags": [
                {
                    "id": "RF-CARDIAC-01",
                    "description": "Chest pain with warning signs",
                    "condition": {"field": "severity", "op": "==", "value": "severe"},
                    "disposition": "EMERGENCY",
                }
            ],
            "disposition_rules": [
                {"condition": {"field": "default", "op": "==", "value": True}, "disposition": "URGENT_CARE"}
            ],
            "safety_netting": "Seek urgent help.",
        }
    )

    assert protocol.red_flags[0].disposition == "EMERGENCY"
    assert protocol.disposition_rules[0].disposition == "URGENT_CARE"


def test_extracted_facts_model_uses_default_lists():
    facts = ExtractedFacts(symptom_category="chest_pain", raw_text="Chest pain for 20 minutes")

    assert facts.associated_symptoms == []
    assert facts.explicit_negatives == []
    assert facts.history_flags == []
    assert facts.duration_minutes is None
