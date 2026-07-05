import asyncio

from triage_copilot.explanation.explanation_generator import (
    build_explanation_prompt,
    fallback_template_explanation,
    generate_explanation,
    is_grounded,
)
from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol
from triage_copilot.questioning.question_selector import SimpleTextResponse, phrase_question


class StubResponse:
    def __init__(self, content):
        self.content = content


class StubLLMClient:
    def __init__(self, content):
        self.content = content

    async def complete(self, task, prompt, response_model):
        return response_model(content=self.content)


def test_phrase_question_uses_llm_client(monkeypatch):
    async def run_test():
        monkeypatch.setattr("triage_copilot.questioning.question_selector.llm_client", StubLLMClient("Can you tell me more about your symptoms?"))
        response = await phrase_question("severity", Protocol(protocol_id="p", symptom_category="chest_pain", required_fields=["severity"]))
        assert response == "Can you tell me more about your symptoms?"

    asyncio.run(run_test())


def test_build_explanation_prompt_contains_disposition_and_safety_text():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="pain")
    protocol = Protocol(protocol_id="p", symptom_category="chest_pain", required_fields=[], safety_netting="Seek care if worsening")
    prompt = build_explanation_prompt(type("Result", (), {"disposition": "PRIMARY_CARE"})(), facts, protocol.safety_netting)

    assert "PRIMARY_CARE" in prompt
    assert "Seek care if worsening" in prompt


def test_is_grounded_rejects_unfounded_symptom_mentions():
    facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="chest pain")
    assert is_grounded("You have nausea", facts, None) is False


def test_generate_explanation_falls_back_when_not_grounded(monkeypatch):
    async def run_test():
        monkeypatch.setattr("triage_copilot.explanation.explanation_generator.llm_client", StubLLMClient("You have nausea"))
        facts = ExtractedFacts(symptom_category="chest_pain", severity="mild", raw_text="chest pain")
        protocol = Protocol(protocol_id="p", symptom_category="chest_pain", required_fields=[], safety_netting="Seek care if worsening")
        result = await generate_explanation(type("Result", (), {"disposition": "PRIMARY_CARE"})(), facts, protocol)
        assert "primary care provider" in result.lower()
        assert "Seek care if worsening" in result

    asyncio.run(run_test())
