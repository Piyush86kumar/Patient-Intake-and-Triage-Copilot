# Decision Log

## Architecture decisions

### No LangChain / LangGraph
**Decision:** Use raw `openai` SDK compatibility layer instead of LangChain or LangGraph.
**Why:** The system has exactly three LLM touchpoints (fact extraction, question phrasing, explanation generation), each with a single call per turn. The orchestration layer (`process_turn()` in `state_machine.py`) is ~35 lines of deterministic Python — a DAG/chaining framework would add more abstraction surface than logic. The `openai` SDK's drop-in compatibility across NVIDIA NIM, Google AI Studio (OpenAI-compatible endpoint), and OpenRouter gets us provider diversity with zero framework overhead.
**Trade-off:** If the system ever needs multi-step LLM chains, tool use, or agentic loops, LangGraph would become worthwhile. At the current scope, it's premature.

### Trigger keywords vs LLM for emergency detection
**Decision:** Use a deterministic keyword list (`safety/trigger_keywords.py`) as the first layer of emergency detection, before any LLM call.
**Why:** The brief explicitly says "don't trust the LLM alone for safety." A keyword list is O(n) substring matching — zero latency, zero cost, zero API dependency. It catches clear trauma/emergency language ("gunshot", "can't breathe", "unconscious") even when the LLM extraction step mis-parses or is unavailable.
**Trade-off:** The keyword list is a blunt instrument — it may false-fire on metaphorical language ("I'm drowning in work"). For a demo/synthetic-data system, this is acceptable. In production, it would need tuning and monitoring.

### Three providers, not one
**Decision:** Primary/fallback per task across NVIDIA NIM, Google AI Studio, and OpenRouter.
**Why:** Provider diversity means no single API key or endpoint is a total outage. NVIDIA NIM is self-hostable (privacy-sensitive extraction). Google AI Studio gives direct access to Gemini (best explanation quality). OpenRouter serves as a cheap generic fallback for all tasks.
**Trade-off:** Three API keys to manage. If any provider changes its OpenAI-compatibility endpoint, the corresponding `base_url` in `.env` needs updating.

### Structured condition evaluation, not raw strings or eval()
**Decision:** Protocol conditions use a nested `{field, op, value}` / `{all, any}` structure evaluated by a recursive `evaluate()` function in `guidance/schema.py`.
**Why:** Never let a config file contain executable code that gets `eval()`'d against patient data. The structured format is type-safe, introspectable, and enforces a bounded operator set at the Pydantic validation layer.
**Impact:** Adding a new operator (e.g., `between`) requires touching both the `Condition` model's `op` literal and the `evaluate()` function's dispatch table.

### SQLite, not Postgres
**Decision:** Single-file SQLite for persistence.
**Why:** Sufficient for a demo with synthetic data. Zero infrastructure, zero config, portable.
**Production gap:** Concurrent write load requires managed Postgres. Named explicitly in the production-readiness doc.

### In-process CLI/Gradio, not HTTP client-server
**Decision:** Both `cli/chat.py` and `ui/gradio_app.py` call `process_turn()` directly (same process), not through the FastAPI endpoints.
**Why:** Fastest possible development loop — no HTTP serialization, no server restart needed for CLI testing. The FastAPI endpoints exist for integration/client use.
**Trade-off:** The CLI and UI share the same process memory. If the controller crashes, the UI goes down with it.

### Gradio mounted inside FastAPI
**Decision:** Mount Gradio UI at `/ui` via `gr.mount_gradio_app()` in `api/main.py`.
**Why:** Single `uvicorn` command serves both REST API and web UI on one port. No separate Gradio process to manage.

### No fine-tuning or vector DB
**Decision:** Hand-authored YAML protocols + category-keyed lookup.
**Why:** Six symptom categories is far too small to justify a vector DB or fine-tuned model. YAML is human-readable, auditable, and loads in milliseconds.

## Out of scope (explicitly)

- Postgres/Redis — SQLite sufficient for demo
- Kubernetes/OpenTelemetry/Grafana/Prometheus/Celery — structured JSON logs (structlog) sufficient for inspectability
- LiteLLM or heavyweight provider-gateway — `openai` SDK compatibility covers all three providers
- Fine-tuning or vector DB/RAG — protocol set is too small
- Real multi-tenant auth — placeholder `API_KEY` header only
- HIPAA/compliance implementation — synthetic data only

## Known trade-offs accepted

- Disposition engine (`disposition_engine.py`) uses `_depends_on_missing_fields()` to defer when required fields are null — a heuristic that favors caution over guessing.
- Extraction prompt explicitly biases toward capturing weak signals ("treat hedged language as present"). This will cause false positives for genuinely low-acuity cases where the patient happens to hedge. The red-flag detector and disposition rules are the safety net.
- `SYNTHETIC_DATA_ONLY=true` emits a startup warning log — no runtime enforcement.
