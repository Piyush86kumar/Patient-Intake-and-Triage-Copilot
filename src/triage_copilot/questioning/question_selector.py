from __future__ import annotations

from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.schema import Protocol


def next_missing_field(facts: ExtractedFacts, protocol: Protocol) -> str | None:
    """Return the first required field that is not yet present or non-null in the facts."""

    payload = facts.model_dump()
    for field in protocol.required_fields:
        value = payload.get(field, getattr(facts, field, None))
        if value in (None, "", [], {}):
            return field

    return None


__all__ = ["next_missing_field"]
