# Triage Copilot

A modular triage assistant for patient symptom intake — extracts facts, detects red flags, matches protocols, asks targeted follow-up questions, and recommends a care level (self-care, primary care, urgent care, or emergency).

## Project Overview

The system implements an agentic triage workflow:

1. **Out-of-scope filter** — Fast keyword check catches diet plans, diagnosis-seeking, prescription refills, and other non-triage questions before any pipeline logic runs.
2. **Fact extraction** — LLM-assisted (with heuristic fallback) extracts symptom category, severity, duration, associated symptoms, and history from patient text.
3. **Red-flag detection** — Two passes: trigger keywords (zero latency, deterministic), then protocol-specific rules (also deterministic, no LLM). Runs *before* any disposition logic.
4. **Protocol matching** — Maps symptom category to one of 7 YAML-defined protocols (chest pain, shortness of breath, severe bleeding/trauma, headache, abdominal pain, sore throat, and a fallback).
5. **Targeted questioning** — Asks only for missing required fields (e.g., severity, duration) — not an exhaustive interview.
6. **Disposition** — Evaluates protocol rules in order: mild→PRIMARY_CARE, moderate→URGENT_CARE, severe→EMERGENCY (via red flags), default→URGENT_CARE (safety net).
7. **Explanation** — LLM-generated (or human-readable fallback) citing the specific facts and rules that drove the recommendation, plus the protocol's safety-netting text.

## Key Components

- `src/triage_copilot/config.py` — application settings, model registry, and provider config
- `src/triage_copilot/extraction/` — fact extraction prompt builder, extractor, and schema
- `src/triage_copilot/guidance/` — protocol schema, loader, and matcher
- `src/triage_copilot/safety/` — red flag detection logic (trigger keywords + protocol conditions)
- `src/triage_copilot/disposition/` — disposition rule evaluation
- `src/triage_copilot/controller/` — patient case persistence and turn-processing state machine
- `src/triage_copilot/api/main.py` — FastAPI app
- `cli/chat.py` — local interactive chat loop
- `eval/run_eval.py` — evaluation runner for JSONL case playback and metrics

## Installation

1. Create and activate your Python virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Configure runtime environment.

Create a `.env` file in the repository root or set environment variables directly:

- `NVIDIA_NIM_BASE_URL`
- `NVIDIA_NIM_API_KEY`
- `GOOGLE_AI_STUDIO_BASE_URL`
- `GOOGLE_AI_STUDIO_API_KEY`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_API_KEY`
- `API_KEY` (default: `changeme_local_dev_key`)
- `SYNTHETIC_DATA_ONLY` (set `true` for development/demo without real patient data)

Optional overrides:
- `TRIAGE_COPILOT_ENV_FILE`
- `MAX_QUESTIONS_PER_CONVERSATION` (default: 8)
- `LLM_REQUEST_TIMEOUT_SECONDS` (default: 15)
- `APP_HOST`, `APP_PORT`, `APP_LOG_LEVEL`

## Usage

### Run the CLI chat loop

```powershell
python cli/chat.py
```

The CLI uses a fixed conversation id (`local-dev`) — the system automatically resets per-turn state when the user describes a new complaint.

### Run the FastAPI app

```powershell
uvicorn triage_copilot.api.main:app --reload --host 0.0.0.0 --port 8000
```

Use the header `X-API-Key` with the configured `API_KEY` value.

Available endpoints:
- `POST /conversations` — create a new conversation
- `POST /conversations/{id}/messages` — submit a user message and process the next turn
- `GET /conversations/{id}/state` — inspect the saved case state

### Run with Docker

```powershell
docker compose up --build
```

Builds and starts the FastAPI server.

### Run tests

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest -q
```

### Run evaluation

```powershell
python eval/run_eval.py
```

Results are written to `eval/results/evaluation_results.json` and `eval/results/evaluation_results.csv`.

## Project Structure

```
triage-copilot/
├── cli/chat.py                 # Interactive CLI
├── protocols/                  # YAML protocol definitions
│   ├── chest_pain.yaml
│   ├── headache.yaml
│   ├── abdominal_pain.yaml
│   ├── sore_throat.yaml
│   ├── shortness_of_breath.yaml
│   ├── severe_bleeding_trauma.yaml
│   └── fallback_no_match.yaml
├── src/triage_copilot/
│   ├── api/main.py             # FastAPI app
│   ├── config.py               # Settings + model registry
│   ├── controller/
│   │   ├── state_machine.py    # process_turn() orchestrator
│   │   └── patient_case.py     # SQLite persistence
│   ├── disposition/
│   │   └── disposition_engine.py
│   ├── explanation/
│   │   └── explanation_generator.py
│   ├── extraction/
│   │   ├── fact_extractor.py   # LLM + heuristic fallback
│   │   ├── prompts.py
│   │   └── schema.py
│   ├── guidance/
│   │   ├── matcher.py
│   │   ├── protocol_store.py
│   │   └── schema.py           # Condition, evaluate()
│   ├── llm/client.py           # Multi-provider retry
│   ├── questioning/
│   │   └── question_selector.py
│   └── safety/
│       ├── red_flag_detector.py
│       └── trigger_keywords.py # 60+ emergency keywords
├── models.yaml                 # LLM provider/task config
├── Dockerfile
├── docker-compose.yml
├── ARCHITECTURE.md
├── DECISION_LOG.md
└── PRODUCTION_READINESS.md
```

## Architecture Decisions

- **No LangChain/LangGraph** — three LLM touchpoints (fact extraction, question phrasing, explanation generation), each a single call per turn. The orchestration is ~80 lines of Python in `state_machine.py`. See `DECISION_LOG.md` for the full reasoning.
- **Deterministic red-flag detector** — keyword triggers + protocol conditions run before any LLM call. Zero latency, zero cost, no API dependency for the safety layer.
- **Protocol-driven disposition** — disposition rules are in YAML, not code. Adding a new protocol means adding a YAML file, no Python changes.
- **Heuristic fallback** — when the LLM extraction fails (timeout, API error), a keyword/regex-based fallback produces facts. Covers all 6 symptom categories with duration (including typo tolerance like `3o mins` → `30 mins`), severity, and associated symptom extraction.
- **Out-of-scope classifier** — runs before any other logic to catch non-triage inputs (diet plans, diagnosis-seeking, prescription management) with a clear, human-friendly response.
- **SQLite** — sufficient for demo/single-instance. See `PRODUCTION_READINESS.md` for production scaling considerations.

## Limitations

- The heuristic fallback does not handle negation ("no shortness of breath" still matches `shortness_of_breath`). The LLM handles this correctly when available.
- No dedicated fever/cold/flu protocol — these fall through to the catch-all protocol.
- Safety-netting text is defined in every protocol YAML but is not yet appended to LLM-generated explanations (only included in the fallback template).
- The medication and out-of-scope detectors are keyword-based and may miss novel phrasings.
