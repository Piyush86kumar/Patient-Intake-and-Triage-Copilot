# Triage Copilot

A modular triage assistant for patient symptom intake, fact extraction, safety red-flag detection, protocol-based dispositioning, and evaluation.

## Project Overview

This repository implements a triage workflow with:
- structured symptom protocols and recursive condition evaluation
- deterministic red-flag detection before dispositioning
- LLM-assisted fact extraction and question phrasing
- persistent case state in SQLite
- a simple FastAPI REST API and local CLI chat loop
- evaluation utilities for metrics and case-based results

## Key Components

- `src/triage_copilot/config.py` — application settings, model registry, and provider config
- `src/triage_copilot/extraction/` — fact extraction prompt builder, extractor, and schema
- `src/triage_copilot/guidance/` — protocol schema, loader, and matcher
- `src/triage_copilot/safety/` — red flag detection logic
- `src/triage_copilot/disposition/` — disposition rule evaluation
- `src/triage_copilot/controller/` — patient case persistence and turn-processing state machine
- `src/triage_copilot/api/main.py` — FastAPI app for conversation endpoints
- `cli/chat.py` — local interactive chat loop for manual testing
- `eval/run_eval.py` — evaluation runner for JSONL case playback and metrics
- `src/triage_copilot/eval/metrics.py` — evaluation metrics computation

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

Create a `.env` file in the repository root or set environment variables directly. Required settings include:

- `NVIDIA_NIM_BASE_URL`
- `NVIDIA_NIM_API_KEY`
- `GOOGLE_AI_STUDIO_BASE_URL`
- `GOOGLE_AI_STUDIO_API_KEY`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_API_KEY`
- `API_KEY`

Optional override:
- `TRIAGE_COPILOT_ENV_FILE`

## Usage

### Run the CLI chat loop

```powershell
python cli/chat.py
```

The CLI uses a local conversation id and calls the controller directly for fast manual testing.

### Run the FastAPI app

```powershell
uvicorn triage_copilot.api.main:app --reload --host 0.0.0.0 --port 8000
```

Use the header `X-API-Key` with the configured `API_KEY` value.

Available endpoints:
- `POST /conversations` — create a new conversation
- `POST /conversations/{id}/messages` — submit a user message and process the next turn
- `GET /conversations/{id}/state` — inspect the saved case state

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

- `models.yaml` — LLM provider/task configuration
- `protocols/` — YAML protocol definitions loaded at runtime
- `data/` — persistent data storage and SQLite database files
- `tests/` — unit and integration test suites
- `eval/cases/` — JSONL evaluation cases
- `eval/results/` — generated evaluation artifacts

## Notes

- The system is designed to keep safety deterministic: red flags and disposition rules are evaluated before final recommendations.
- The LLM is used for structured fact extraction, question phrasing, and explanations, but the core triage logic is schema-driven.
- If provider access is unavailable, the evaluation runner may still fall back to heuristic extraction behavior.
