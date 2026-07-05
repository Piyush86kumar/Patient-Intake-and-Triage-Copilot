from __future__ import annotations

from triage_copilot.explanation.explanation_generator import is_grounded
from triage_copilot.extraction.schema import ExtractedFacts


def compute_metrics(results: list[dict]) -> dict[str, float]:
    total_emergencies = sum(1 for row in results if row.get("expected_disposition") == "EMERGENCY")
    red_flag_hits = sum(
        1
        for row in results
        if row.get("expected_disposition") == "EMERGENCY" and row.get("actual_disposition") == "EMERGENCY"
    )

    non_emergency_results = [row for row in results if row.get("expected_disposition") != "EMERGENCY"]
    non_emergency_correct = sum(
        1
        for row in non_emergency_results
        if row.get("actual_disposition") == row.get("expected_disposition")
    )

    grounded_passes = sum(1 for row in results if row.get("grounded") is True)

    return {
        "red_flag_recall": red_flag_hits / total_emergencies if total_emergencies else 1.0,
        "disposition_accuracy_non_emergency": non_emergency_correct / len(non_emergency_results) if non_emergency_results else 1.0,
        "groundedness_pass_rate": grounded_passes / len(results) if results else 1.0,
    }


def evaluate_groundedness(facts: ExtractedFacts, explanation: str) -> bool:
    return is_grounded(explanation, facts, None)


__all__ = ["compute_metrics", "evaluate_groundedness"]
