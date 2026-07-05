# Triage Copilot — Architecture

## Overview

A modular triage assistant for patient symptom intake. The system combines deterministic, schema-driven triage logic (protocols, red-flag detection, disposition rules) with LLM-assisted fact extraction, question phrasing, and explanation generation.

```
Patient message
      │
      ▼
┌─────────────────────────────┐
│  CONVERSATION CONTROLLER     │  state machine, owns PatientCase (SQLite)
│  (controller/state_machine)  │  enforces red-flag check on EVERY turn,
└──────────────┬───────────────┘  unconditionally, before any other branch
               │ 1. raw text
               ▼
     ┌────────────────────┐
     │  FACT EXTRACTOR      │  LLM call → task: fact_extraction
     │  (extraction/)       │  primary: NVIDIA NIM · fallback: OpenRouter
     └─────────┬─────────────┘  schema-validated (ExtractedFacts) before use
               │ 2. structured facts
               ▼
     ┌─────────────────────────────┐
     │  RED-FLAG DETECTOR            │  pure Python, zero I/O, runs every turn
     │  (safety/)                    │  Layer 1: raw-text trigger keywords
     │                                │  Layer 2: structured protocol red_flags
     └─────────┬──────────────────────┘
     fired? ──Yes──► EMERGENCY — fixed template response, zero extra LLM calls
               │ No
               ▼
     ┌────────────────────────┐
     │  GUIDANCE MATCHER        │  in-memory YAML lookup, no I/O
     │  (guidance/)              │  falls back to fallback_no_match protocol
     └─────────┬──────────────────┘
               │ 3. matched protocol
               ▼
     ┌────────────────────────┐
     │  QUESTION SELECTOR       │  checklist-driven — finds next missing field
     │  (questioning/)           │  LLM phrases it → task: question_phrasing
     └─────────┬──────────────────┘  primary: OpenRouter (small/cheap model)
               │ Not enough info → loop
               │ Enough info, or question budget exhausted
               ▼
     ┌────────────────────────┐
     │  DISPOSITION ENGINE       │  pure Python, ordered rule evaluation,
     │  (disposition/)            │  most-severe-first, bias toward caution
     └─────────┬──────────────────┘
               │ 4. disposition + cited rule ID
               ▼
     ┌────────────────────────────┐
     │  EXPLANATION GENERATOR       │  LLM call → task: explanation_generation
     │  (explanation/)                │  primary: Google AI Studio (Gemini)
     │                                 │  fallback: OpenRouter
     └─────────┬────────────────────────┘  groundedness-checked before returning
               │ 5. patient-facing message
               ▼
         Patient receives reply
```

## Key architectural guarantee

The Red-Flag Detector (`safety/red_flag_detector.py`) sits between Fact Extraction and Guidance Matching in the control flow, and runs unconditionally on every turn — never skipped, never model-decided. This is enforced in `controller/state_machine.py:process_turn()`: `check_red_flags()` is called at line 70, before `match_protocol()` at line 81.

## Core modules (src/triage_copilot/)

| Module | Files | Role |
|--------|-------|------|
| `api/` | `main.py` | FastAPI endpoints: `POST /conversations`, `POST /conversations/{id}/messages`, `GET /conversations/{id}/state`. Gradio UI mounted at `/ui`. |
| `controller/` | `patient_case.py`, `state_machine.py` | `PatientCase` SQLite persistence; `process_turn()` — the orchestration core. |
| `disposition/` | `disposition_engine.py` | `decide_disposition()` — deterministic, ordered rule evaluation; returns `None` if required fields missing. |
| `explanation/` | `explanation_generator.py` | `generate_explanation()` — LLM call with `is_grounded()` check and fallback template. |
| `extraction/` | `fact_extractor.py`, `prompts.py`, `schema.py` | `extract_facts()` — LLM call to parse free text into `ExtractedFacts`; heuristic fallback on LLM failure. |
| `guidance/` | `schema.py`, `protocol_store.py`, `matcher.py` | `Protocol` model, YAML loading/validation at startup, `match_protocol()` with fallback. |
| `llm/` | `client.py` | `LLMClient.complete()` — retry-then-fallback across primary/fallback providers per `models.yaml`. |
| `logging/` | `__init__.py` | structlog-style helper. |
| `questioning/` | `question_selector.py` | `next_missing_field()` — returns first missing required field; `phrase_question()` — LLM call for natural-language follow-up. |
| `safety/` | `red_flag_detector.py`, `trigger_keywords.py` | `check_red_flags()` — raw-text keyword scan + protocol condition evaluation. Zero LLM calls. |

## Interfaces

- **CLI** (`cli/chat.py`): calls `process_turn()` directly (in-process) for fast manual testing.
- **Gradio UI** (`ui/gradio_app.py`): mounted inside FastAPI at `/ui`. Two tabs: Patient Chat and Clinician View (real `PatientCase` state).
- **FastAPI** (`api/main.py`): serves REST API + Gradio UI from one process.

## Data flow

1. Patient sends free-text message
2. `extract_facts()` (LLM) → structured `ExtractedFacts`
3. `check_red_flags()` (deterministic) → EMERGENCY or continue
4. `match_protocol()` (YAML lookup) → best protocol or fallback
5. `next_missing_field()` (checklist) → ask question or proceed
6. `decide_disposition()` (rule engine) → disposition
7. `generate_explanation()` (LLM + groundedness check) → patient-facing message

Each step writes a structured JSON event (structlog) keyed by conversation ID.

## Protocols

Seven YAML protocols under `protocols/` define symptom categories, required fields, red-flag conditions, disposition rules, and safety-netting text. All conditions use a safe recursive `{field, op, value}` / `{all, any}` structure — no `eval()`.

## Persistence

Single-table SQLite via `PatientCase` in `controller/patient_case.py`. One `patient_cases` table storing conversation state as serialized JSON.

## Deployment

Single process: `uvicorn triage_copilot.api.main:app --host 0.0.0.0 --port 8000` serves API + UI on one port. Dockerfile provided for containerized deployment.
