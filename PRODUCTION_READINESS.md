# Production Readiness — If This Were Going to Production

## Scale

- **Stateless API pods** behind a load balancer. The controller state lives in SQLite per pod — this would need to move to a shared managed Postgres instance for horizontal scaling.
- **LLM call decoupling.** At production load, the synchronous LLM calls inside `process_turn()` would block the request/response cycle. A queue (SQS/Celery) between the controller and the LLM client would allow async processing with proper timeout/retry.
- **Connection pooling.** The SQLite connection in `patient_case.py` opens/closes per operation — fine for demo volumes but not for concurrent production traffic.

## Cost

- Two LLM calls per turn on average (extraction + one of question-phrasing or explanation).
- Current `models.yaml` assigns: extraction → NVIDIA NIM (Llama 3.1 70B), question-phrasing → OpenRouter (Gemma 3 12B), explanation → Google AI Studio (Gemini 3.5 Flash).
- Extraction is the most expensive call (70B param model). If cost is a concern at volume, swap to OpenRouter's free-tier models for extraction and reserve the high-quality model for explanation only.

## Safety monitoring

- **Red-flag rule fire-rate anomalies.** A sudden drop in EMERGENCY fire rate could indicate a regression in the keyword list or protocol conditions. Route structured logs to a monitoring system with alerting on rate changes.
- **No-protocol-match replay.** Periodically replay conversations that matched `fallback_no_match` to identify coverage gaps. Expand protocols and trigger keywords accordingly.
- **Groundedness pass-rate tracking.** The `is_grounded()` check in `explanation_generator.py` is a simple keyword-presence heuristic. In production, a dedicated NLI (natural language inference) model would be more robust. Track the pass rate and alert on drops.

## Compliance

- **BAAs** (Business Associate Agreements) required with every model provider touching patient text — NVIDIA, Google, and OpenRouter (which fronts Anthropic, Google, and other models).
- **PHI encryption in transit and at rest.** TLS for all API endpoints. Database encryption at rest (SQLite itself doesn't support this; managed Postgres with TDE would be the production path).
- **Audit logging.** Every turn writes a structured JSON event (structlog) with conversation ID, timestamp, facts extracted, red-flag result, matched protocol, disposition, and which provider/model handled each LLM call. This must be stored in an append-only log for audit compliance.
- **Data retention policy.** Patient text in `ExtractedFacts.raw_text` is stored indefinitely in the current SQLite schema. A production system needs configurable retention (e.g., 30/60/90 day auto-purge with a safe harbor for ongoing cases).

## Gaps for production (not implemented)

- Real auth (OAuth2/JWT) — currently a single API key placeholder
- Rate limiting per conversation/client
- Structured error responses with proper HTTP status codes for all LLM failure modes
- Health check endpoint (`GET /health`) with provider status
- Database migration tooling (Alembic or similar)
- Container orchestration readiness (health checks, graceful shutdown, config via env vars not files)
