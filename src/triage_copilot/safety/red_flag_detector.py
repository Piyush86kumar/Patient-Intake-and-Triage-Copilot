from __future__ import annotations

from pydantic import BaseModel

from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol, RedFlag, evaluate
from triage_copilot.safety.trigger_keywords import check_trigger_keywords


class RedFlagResult(BaseModel):
    fired: bool
    rule_id: str | None = None
    disposition: str | None = None


def check_red_flags(facts: ExtractedFacts, raw_text: str, protocol: Protocol | None) -> RedFlagResult:
    """Evaluate emergency trigger keywords and protocol red flags without any I/O or LLM calls."""

    if check_trigger_keywords(raw_text):
        return RedFlagResult(fired=True, rule_id="TRIGGER-KEYWORD", disposition="EMERGENCY")

    if protocol is None:
        return RedFlagResult(fired=False)

    facts_payload = facts.model_dump()
    for red_flag in protocol.red_flags:
        if evaluate(red_flag.condition, facts_payload):
            return RedFlagResult(fired=True, rule_id=red_flag.id, disposition=red_flag.disposition)

    return RedFlagResult(fired=False)


__all__ = ["RedFlagResult", "check_red_flags"]
