# Patient Intake & Triage Copilot

An agentic system that accepts a patient's free-text symptom description, asks targeted follow-up questions, checks for medical emergencies with a deterministic (zero-LLM, zero-latency) red-flag detector, matches against synthetic triage protocols, and recommends a care level: self-care, primary care, urgent care, or emergency. This is a **care navigation** prototype, not a diagnosis tool — it routes patients to the right level of care based on protocol rules and must never be used with real patient data.

## Quick Start

**Primary (Docker):** Copy `.env.example` to `.env`, add API keys for at least one of the three providers (NVIDIA NIM, OpenRouter, Google AI Studio), then:

```
docker compose up --build
```

The API serves at `http://localhost:8000`. See `.env.example` for all config values.

**Alternative (local venv):**

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn triage_copilot.api.main:app --host 0.0.0.0 --port 8000
```

Or use the interactive CLI: `.venv\Scripts\python cli/chat.py`

## Exercise the API

All endpoints require an `X-API-Key` header (default: `changeme_local_dev_key`).

```
# Create a conversation
curl -s -X POST http://localhost:8000/conversations \
  -H "X-API-Key: changeme_local_dev_key"

# → {"conversation_id":"abc-123"}

# Chest pain emergency case (should return status: EMERGENCY)
curl -s -X POST http://localhost:8000/conversations/abc-123/messages \
  -H "X-API-Key: changeme_local_dev_key" \
  -H "Content-Type: application/json" \
  -d '{"message":"crushing chest pain for 30 minutes, short of breath and sweaty"}'

# Mild sore throat case (should return status: DISPOSITION_GIVEN)
curl -s -X POST http://localhost:8000/conversations/abc-124/messages \
  -H "X-API-Key: changeme_local_dev_key" \
  -H "Content-Type: application/json" \
  -d '{"message":"mild sore throat since yesterday, no fever, no trouble breathing or swallowing"}'
```

Inspect conversation state at `GET /conversations/{id}/state` to see extracted facts, matched protocol, disposition, and turn count.

## Architecture

Patient messages flow through fact extraction (LLM + heuristic fallback), a deterministic red-flag check (keyword layer then protocol conditions), YAML-driven protocol matching, next-question selection (LLM-phrased, checklist-guided), disposition rule evaluation, and explanation generation. A FastAPI controller with SQLite persistence manages the turn loop. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full diagram.

## Tests & Eval

```
pytest                           # 35 unit tests
python eval/run_eval.py          # 11 eval cases → eval/results/
```

The eval suite runs each JSONL case through the full conversation loop, records actual vs expected disposition, and computes groundedness metrics.

## Data & Safety

All patient data is synthetic. The `SYNTHETIC_DATA_ONLY=true` flag is the default in `.env.example` and enforced by a startup warning. No real PHI should ever enter this system. The red-flag detector is entirely deterministic — keyword matching plus protocol conditions, zero LLM calls — and runs on every turn before any other branch.

## Other Docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DECISION_LOG.md](DECISION_LOG.md)
- [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md)
