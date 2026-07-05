from __future__ import annotations

from triage_copilot.extraction.schema import ExtractedFacts
from triage_copilot.guidance.protocol_store import protocol_store
from triage_copilot.guidance.schema import Protocol


def _keyword_overlap(facts: ExtractedFacts, protocol: Protocol) -> int:
    target = (facts.symptom_category or "").lower()
    source = (protocol.symptom_category or "").lower()
    if not target or not source:
        return 0

    target_tokens = set(target.replace("_", " ").split())
    source_tokens = set(source.replace("_", " ").split())
    return len(target_tokens & source_tokens)


def match_protocol(facts: ExtractedFacts) -> Protocol:
    """Match the best protocol by exact symptom category, then keyword overlap, falling back to the no-match protocol."""

    candidates = [protocol for protocol in protocol_store.get_all_protocols() if protocol.protocol_id != "fallback_no_match_v1"]

    exact_matches = [protocol for protocol in candidates if protocol.symptom_category == facts.symptom_category]
    if exact_matches:
        return exact_matches[0]

    scored = [
        (protocol, _keyword_overlap(facts, protocol))
        for protocol in candidates
    ]
    scored = [item for item in scored if item[1] > 0]
    if scored:
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[0][0]

    fallback_protocol = next(
        (protocol for protocol in protocol_store.get_all_protocols() if protocol.protocol_id == "fallback_no_match_v1"),
        None,
    )
    if fallback_protocol is not None:
        return fallback_protocol

    raise RuntimeError("No fallback protocol available")


__all__ = ["match_protocol"]
