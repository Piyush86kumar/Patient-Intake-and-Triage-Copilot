from triage_copilot.disposition.disposition_engine import DispositionResult, decide_disposition
from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol


def test_decide_disposition_returns_first_matching_rule():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="mild chest pain")
    protocol = Protocol.model_validate(
        {
            "protocol_id": "test",
            "symptom_category": "test",
            "disposition_rules": [
                {"condition": {"field": "severity", "op": "==", "value": "severe"}, "disposition": "EMERGENCY"},
                {"condition": {"field": "severity", "op": "==", "value": "mild"}, "disposition": "PRIMARY_CARE"},
            ],
        }
    )

    result = decide_disposition(facts, protocol)

    assert result.disposition == "PRIMARY_CARE"
    assert result.matched_rule is not None
    assert "severity" in result.condition_summary or result.condition_summary is not None


def test_decide_disposition_falls_back_to_default_when_specific_rule_missing_field():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="mild chest pain")
    protocol = Protocol.model_validate(
        {
            "protocol_id": "test",
            "symptom_category": "test",
            "disposition_rules": [
                {"condition": {"field": "shortness_of_breath", "op": "==", "value": True}, "disposition": "EMERGENCY"},
                {"condition": {"field": "default", "op": "==", "value": True}, "disposition": "URGENT_CARE"},
            ],
        }
    )

    result = decide_disposition(facts, protocol)

    assert result.disposition == "URGENT_CARE"
    assert result.matched_rule is not None


def test_decide_disposition_returns_none_when_no_rule_matches():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="mild chest pain")
    protocol = Protocol.model_validate(
        {
            "protocol_id": "test",
            "symptom_category": "test",
            "disposition_rules": [
                {"condition": {"field": "shortness_of_breath", "op": "==", "value": True}, "disposition": "EMERGENCY"},
            ],
        }
    )

    result = decide_disposition(facts, protocol)

    assert result.disposition is None
    assert result.matched_rule is None
