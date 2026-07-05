# Production Readiness

What breaks first at 50K conversations/day, what it costs, and what's missing.

## Scale

**SQLite serializes writes.** At 50K conversations/day, `INSERT ... ON CONFLICT DO UPDATE` per turn locks on every write. Fix: managed Postgres with a connection pool, stateless API pods behind a load balancer.

**LLM calls block the HTTP response.** Each turn makes up to 2 sequential calls (extraction + question or explanation). At 15s per attempt, a turn stalls 30s+ when the primary times out. A work queue decouples the response from LLM I/O — return `202 Accepted` with a polling token, process the turn asynchronously.

## Cost

Per turn: **2 LLM calls maximum** (extraction always, plus question phrasing or explanation). Typical 3-turn conversation: 6 calls. Emergency: 1 call.

| Task | Model | Est. price per call |
|---|---|---|
| Extraction (primary) | `google/gemma-4-31b-it:free` | $0 (free tier) |
| Extraction (fallback) | `meta/llama-3.1-70b-instruct` (NVIDIA) | ~$0.001 |
| Question phrasing | `google/gemma-3-12b-it` (OpenRouter) | ~$0.00004 |
| Explanation (primary) | `gemini-3.5-flash` (Google AI) | ~$0.00009 |
| Explanation (fallback) | `claude-3.5-sonnet` (OpenRouter) | ~$0.004 |

Best case (all primaries succeed): ~$0.0003/conversation — ~**$450/month** at 50K/day. Worst case (free tier exhausted, all fallbacks fire): ~$0.02/conversation — ~**$30K/month**. The spread is dominated by claude-3.5-sonnet at ~50x gemini-flash for explanation.

## Latency

Fact extraction is the bottleneck — most tokens, runs every turn. Explanation generation is close but only fires on the terminal turn. The two sequential calls are the floor latency. Mitigations: smaller extraction model, cache identical message extractions, pre-generate explanations after disposition.

## Safety Monitoring

Two uninstrumented metrics: red-flag fire rate per protocol (a drop means a regression) and `fallback_no_match` rate (each hit is a coverage gap). Both need dashboards with anomaly alerts.

## Compliance Gaps

None of this is built — synthetic data only. Required before real PHI: BAAs with all three providers, TLS everywhere, encryption at rest, audit logging on every access, data retention and deletion policy.

## Next Steps (one week)

1. **Move extraction to a paid model.** The free tier has no SLA and unknown rate limits. A small paid model makes latency and cost predictable.
2. **Log every LLM call.** Prompt size, response time, token count, retry count per provider. Without this, cost and latency are guesswork.
3. **Add a circuit breaker to the LLM client.** Stop calling a provider after sustained 429s/500s instead of burning retries on every request.
