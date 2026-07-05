from __future__ import annotations

import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from triage_copilot.controller.patient_case import CaseStatus, PatientCase
from triage_copilot.controller.state_machine import process_turn
from triage_copilot.eval.metrics import compute_metrics, evaluate_groundedness


BASE_DIR = Path(__file__).resolve().parent
CASES_DIR = BASE_DIR / "cases"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


async def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    conversation_id = f"eval-{case['id']}"
    case_obj = PatientCase.new(conversation_id)
    case_obj.save()

    initial_text = case.get("text", "")
    scripted_turns = case.get("turns") or []

    try:
        response = await process_turn(conversation_id, initial_text)
        final_case = PatientCase.load(conversation_id)
        for turn in scripted_turns:
            if final_case is not None and final_case.status in {CaseStatus.EMERGENCY, CaseStatus.DISPOSITION_GIVEN}:
                break
            response = await process_turn(conversation_id, turn)
            final_case = PatientCase.load(conversation_id)

        if final_case is None:
            raise RuntimeError("conversation state was not created")

        actual_disposition = final_case.disposition or ("EMERGENCY" if final_case.status == CaseStatus.EMERGENCY else response.status)
        explanation = response.message
        grounded = evaluate_groundedness(final_case.facts, explanation)
    except Exception as exc:  # pragma: no cover - defensive eval path
        return {
            "id": case.get("id"),
            "expected_disposition": case.get("expected_disposition"),
            "actual_disposition": None,
            "status": "ERROR",
            "message": str(exc),
            "grounded": False,
        }

    return {
        "id": case.get("id"),
        "expected_disposition": case.get("expected_disposition"),
        "actual_disposition": actual_disposition,
        "status": response.status,
        "message": explanation,
        "grounded": grounded,
    }


async def run_evaluation(case_path: Path | None = None) -> list[dict[str, Any]]:
    case_path = case_path or CASES_DIR / "sample_cases.jsonl"
    cases = _load_cases(case_path)
    results = [await _run_case(case) for case in cases]
    metrics = compute_metrics(results)

    output_path = RESULTS_DIR / "evaluation_results.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump({"results": results, "metrics": metrics}, handle, indent=2)

    table_path = RESULTS_DIR / "evaluation_results.csv"
    with table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "expected_disposition", "actual_disposition", "status", "grounded", "message"],
        )
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    return results


def main() -> None:
    results = asyncio.run(run_evaluation())
    print(json.dumps({"results": results, "metrics": compute_metrics(results)}, indent=2))


if __name__ == "__main__":
    main()
