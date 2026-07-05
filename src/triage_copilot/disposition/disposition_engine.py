from __future__ import annotations

from pydantic import BaseModel

from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Condition, DispositionRule, Protocol, evaluate


class DispositionResult(BaseModel):
    disposition: str | None = None
    matched_rule: DispositionRule | None = None
    condition_summary: str | None = None


def _condition_to_text(condition: Condition) -> str:
    if condition.all is not None:
        parts = ["all of: " + ", ".join(_condition_to_text(child) for child in condition.all)]
        return "(" + "; ".join(parts) + ")"
    if condition.any is not None:
        parts = ["any of: " + ", ".join(_condition_to_text(child) for child in condition.any)]
        return "(" + "; ".join(parts) + ")"

    if condition.field is None or condition.op is None:
        return "unspecified condition"

    return f"{condition.field} {condition.op} {condition.value!r}"


def _depends_on_missing_fields(condition: Condition, facts: ExtractedFacts) -> bool:
    if condition.all is not None:
        return any(_depends_on_missing_fields(child, facts) for child in condition.all)
    if condition.any is not None:
        return any(_depends_on_missing_fields(child, facts) for child in condition.any)

    if condition.field is None:
        return False

    return condition.field not in facts.model_dump()


def decide_disposition(facts: ExtractedFacts, protocol: Protocol) -> DispositionResult:
    """Evaluate protocol disposition rules in order and return the first match or a deferred result."""

    facts_payload = facts.model_dump()
    for rule in protocol.disposition_rules:
        if _depends_on_missing_fields(rule.condition, facts):
            continue

        if evaluate(rule.condition, facts_payload):
            return DispositionResult(
                disposition=rule.disposition,
                matched_rule=rule,
                condition_summary=_condition_to_text(rule.condition),
            )

    return DispositionResult(disposition=None, matched_rule=None, condition_summary=None)


__all__ = ["DispositionResult", "decide_disposition"]
