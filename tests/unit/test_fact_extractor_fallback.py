import pytest

from triage_copilot.extraction.fact_extractor import extract_facts
from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.llm.client import ExtractionFailedError


@pytest.mark.asyncio
async def test_extract_facts_falls_back_to_heuristics(monkeypatch):
    async def fail_complete(*args, **kwargs):
        raise ExtractionFailedError("offline")

    monkeypatch.setattr("triage_copilot.extraction.fact_extractor.llm_client.complete", fail_complete)

    facts = await extract_facts("probably nothing but chest feels tight and a little short of breath", None)

    assert facts.symptom_category == "chest_pain"
    assert facts.associated_symptoms
    assert "shortness_of_breath" in facts.associated_symptoms
    assert facts.raw_text == "probably nothing but chest feels tight and a little short of breath"
