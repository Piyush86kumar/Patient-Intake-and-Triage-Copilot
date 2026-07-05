import asyncio

from triage_copilot.controller.patient_case import PatientCase
from triage_copilot.controller.state_machine import process_turn
from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.protocol_store import protocol_store


def test_process_turn_initializes_case_and_asks_question(monkeypatch, tmp_path):
    # Use a temp DB for persistence during this test.
    monkeypatch.setattr("triage_copilot.controller.patient_case.DB_PATH", tmp_path / "patient_cases.db")

    async def fake_extract_facts(raw_text, prior_facts):
        return ExtractedFacts(
            symptom_category="chest_pain",
            duration_minutes=None,
            severity=None,
            associated_symptoms=[],
            explicit_negatives=[],
            history_flags=[],
            raw_text=raw_text,
        )

    async def fake_phrase_question(field, protocol):
        return f"Please describe {field}."

    monkeypatch.setattr("triage_copilot.controller.state_machine.extract_facts", fake_extract_facts)
    monkeypatch.setattr("triage_copilot.controller.state_machine.phrase_question", fake_phrase_question)

    response = asyncio.run(process_turn("conv1", "I have chest pain"))

    assert response.status == "GATHERING"
    assert "Please describe" in response.message


def test_process_turn_handles_no_more_questions_as_emergency(monkeypatch, tmp_path):
    monkeypatch.setattr("triage_copilot.controller.patient_case.DB_PATH", tmp_path / "patient_cases.db")

    async def fake_extract_facts(raw_text, prior_facts):
        return prior_facts

    monkeypatch.setattr("triage_copilot.controller.state_machine.extract_facts", fake_extract_facts)
    monkeypatch.setattr("triage_copilot.controller.state_machine.next_missing_field", lambda facts, protocol: None)
    monkeypatch.setattr("triage_copilot.controller.state_machine.decide_disposition", lambda facts, protocol: type("R", (), {"disposition": "PRIMARY_CARE"})())
    monkeypatch.setattr("triage_copilot.controller.state_machine.match_protocol", lambda facts: protocol_store.get_protocol("fallback_no_match_v1"))

    case = PatientCase.new("conv2")
    case.turn_count = 8
    case.save()

    response = asyncio.run(process_turn("conv2", "Still here"))

    assert response.status == "EMERGENCY"
    assert "urgent medical care" in response.message.lower()
