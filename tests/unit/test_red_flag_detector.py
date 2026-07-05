from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol
from triage_copilot.safety.red_flag_detector import RedFlagResult, check_red_flags


def test_keyword_trigger_short_circuits_before_protocol_rules():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="severe bleeding")
    protocol = Protocol.model_validate(
        {
            "protocol_id": "test",
            "symptom_category": "test",
            "red_flags": [
                {
                    "id": "RULE-1",
                    "description": "example",
                    "condition": {"field": "severity", "op": "==", "value": "mild"},
                    "disposition": "PRIMARY_CARE",
                }
            ],
        }
    )

    result = check_red_flags(facts, "severe bleeding", protocol)

    assert result == RedFlagResult(fired=True, rule_id="TRIGGER-KEYWORD", disposition="EMERGENCY")


def test_protocol_rule_is_evaluated_when_no_keyword_matches():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="severe", raw_text="pain")
    protocol = Protocol.model_validate(
        {
            "protocol_id": "test",
            "symptom_category": "test",
            "red_flags": [
                {
                    "id": "RULE-1",
                    "description": "example",
                    "condition": {"field": "severity", "op": "==", "value": "severe"},
                    "disposition": "EMERGENCY",
                }
            ],
        }
    )

    result = check_red_flags(facts, "pain", protocol)

    assert result == RedFlagResult(fired=True, rule_id="RULE-1", disposition="EMERGENCY")


def test_gunshot_phrasing_variant_caught_by_raw_text_trigger():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="someone shot me in the leg")
    protocol = Protocol.model_validate(
        {
            "protocol_id": "test",
            "symptom_category": "test",
            "red_flags": [],
        }
    )

    result = check_red_flags(facts, "someone shot me in the leg", protocol)

    assert result == RedFlagResult(fired=True, rule_id="TRIGGER-KEYWORD", disposition="EMERGENCY")


def test_downplayed_language_still_extracts_and_fires():
    facts = ExtractedFacts(
        symptom_category="chest_pain",
        severity=None,
        associated_symptoms=["shortness_of_breath"],
        duration_minutes=30,
        raw_text="probably nothing but chest feels tight and I'm having trouble breathing",
    )
    protocol = Protocol.model_validate(
        {
            "protocol_id": "chest_pain",
            "symptom_category": "chest_pain",
            "red_flags": [
                {
                    "id": "RF-CARDIAC-01",
                    "description": "Chest pain with cardiac warning signs, short duration",
                    "condition": {
                        "all": [
                            {"field": "duration_minutes", "op": "<", "value": 60},
                            {
                                "any": [
                                    {"field": "associated_symptoms", "op": "contains", "value": "shortness_of_breath"},
                                    {"field": "associated_symptoms", "op": "contains", "value": "sweating"},
                                    {"field": "associated_symptoms", "op": "contains", "value": "radiating_pain"},
                                ]
                            },
                        ]
                    },
                    "disposition": "EMERGENCY",
                }
            ],
        }
    )

    result = check_red_flags(facts, facts.raw_text, protocol)

    assert result.fired is True
    assert result.disposition == "EMERGENCY"


def test_returns_not_fired_when_no_conditions_match():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="pain")
    protocol = Protocol.model_validate(
        {
            "protocol_id": "test",
            "symptom_category": "test",
            "red_flags": [
                {
                    "id": "RULE-1",
                    "description": "example",
                    "condition": {"field": "severity", "op": "==", "value": "severe"},
                    "disposition": "EMERGENCY",
                }
            ],
        }
    )

    result = check_red_flags(facts, "pain", protocol)

    assert result == RedFlagResult(fired=False)
