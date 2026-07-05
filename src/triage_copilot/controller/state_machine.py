from __future__ import annotations

from dataclasses import dataclass

from triage_copilot.config import settings
from triage_copilot.controller.patient_case import PatientCase, CaseStatus
from triage_copilot.disposition.disposition_engine import decide_disposition
from triage_copilot.extraction.fact_extractor import extract_facts
from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.matcher import match_protocol
from triage_copilot.questioning.question_selector import next_missing_field, phrase_question
from triage_copilot.safety.red_flag_detector import check_red_flags
from triage_copilot.explanation.explanation_generator import generate_explanation


@dataclass
class ControllerResponse:
    message: str
    status: str


def get_matched_protocol(case: PatientCase):
    if case.matched_protocol_id:
        from triage_copilot.guidance.protocol_store import protocol_store

        try:
            return protocol_store.get_protocol(case.matched_protocol_id)
        except KeyError:
            return None
    return None


def merge_facts(existing: ExtractedFacts, new_facts: ExtractedFacts) -> ExtractedFacts:
    merged_payload = existing.model_dump()
    merged_payload.update({k: v for k, v in new_facts.model_dump().items() if v not in (None, "", [], {})})
    return ExtractedFacts.model_validate(merged_payload)


def emergency_response_template(red_flag_result):
    return ControllerResponse(
        message=(
            "Emergency red flag detected. Please seek immediate medical attention or call emergency services now."
        ),
        status=CaseStatus.EMERGENCY.value,
    )


def escalation_due_to_uncertainty_template():
    return ControllerResponse(
        message=(
            "We cannot safely determine the next steps because key information is missing and question limits have been reached."
            " Please seek urgent medical care."
        ),
        status=CaseStatus.EMERGENCY.value,
    )


async def process_turn(conversation_id: str, message: str) -> ControllerResponse:
    case = PatientCase.load(conversation_id) or PatientCase.new(conversation_id)
    new_facts = await extract_facts(message, case.facts)
    case.facts = merge_facts(case.facts, new_facts)

    red_flag = check_red_flags(case.facts, message, get_matched_protocol(case))
    if red_flag.fired:
        case.status = CaseStatus.EMERGENCY
        case.save()
        return emergency_response_template(red_flag)

    if case.turn_count >= settings.MAX_QUESTIONS_PER_CONVERSATION:
        case.status = CaseStatus.EMERGENCY
        case.save()
        return escalation_due_to_uncertainty_template()

    protocol = match_protocol(case.facts)
    case.matched_protocol_id = protocol.protocol_id
    missing_field = next_missing_field(case.facts, protocol)

    if missing_field:
        question = await phrase_question(missing_field, protocol)
        case.questions_asked.append(question)
        case.turn_count += 1
        case.save()
        return ControllerResponse(message=question, status=CaseStatus.GATHERING.value)

    disposition_result = decide_disposition(case.facts, protocol)
    if disposition_result.disposition is None:
        case.status = CaseStatus.EMERGENCY
        case.save()
        return escalation_due_to_uncertainty_template()
    explanation = await generate_explanation(disposition_result, case.facts, protocol)
    case.disposition = disposition_result.disposition
    case.status = CaseStatus.DISPOSITION_GIVEN
    case.save()
    return ControllerResponse(message=explanation, status=CaseStatus.DISPOSITION_GIVEN.value)


__all__ = ["ControllerResponse", "process_turn"]
