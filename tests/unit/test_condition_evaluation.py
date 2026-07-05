from triage_copilot.guidance.protocol_store import load_protocol
from triage_copilot.guidance.schema import evaluate

def test_condition_evaluation_matches_hand_trace():
    facts = {"duration_minutes": 30, "associated_symptoms": ["shortness_of_breath"]}
    protocol = load_protocol("protocols/chest_pain.yaml")
    assert evaluate(protocol.red_flags[0].condition, facts) is True