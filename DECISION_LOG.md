# Decision Log

Real engineering notes on what was chosen, what was rejected, and why. Not a diary — just the ones that mattered.

## No LangChain, no LangGraph

The system has exactly three LLM touchpoints (fact extraction, question phrasing, explanation generation), each a single call per turn. The orchestration in `process_turn()` is ~70 lines of Python — a state machine with four branches, not a DAG. Adding LangChain or LangGraph would wrap those 70 lines in abstractions I don't need and would have to debug through. Three `await` calls and an `if/elif/else` is trivially testable; a LangGraph graph isn't. If the system ever needs multi-step agentic loops (LLM calls that feed into each other within a single turn), this decision gets revisited. Until then, no.

## Structured conditions, not eval()

The protocol YAML files define conditions as nested `{field, op, value}` / `{all, any}` dicts. A recursive `evaluate()` function in `guidance/schema.py` walks the tree and dispatches to 8 operators (`==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `contains`). The alternative was storing conditions as Python expression strings and calling `eval()` on them — which is what the brief's schema sample essentially showed. I rejected that because a config file that gets `eval()`'d against patient data is one YAML injection away from arbitrary code execution. The structured format is type-safe (Pydantic validates it at load time), introspectable (you can dump and log the condition tree), and bounded — no operator can appear that isn't in the Literal union. The cost: adding a new operator means touching both the model and the dispatch table. Fine by me.

## Deterministic red-flag detector, not LLM-based

Emergency detection uses two pure-Python layers running in sequence: 79 trigger keywords on the raw text, then structured protocol-condition evaluation on the extracted facts. Zero I/O, zero LLM calls, zero latency. The rejected alternative was to have the LLM extraction step determine if symptoms are emergencies. That was never viable — if the LLM is down (timeout, API error, rate limit) the safety layer can't depend on it. The keyword list is a blunt instrument (false-positives on metaphorical language like "drowning in work"), but it's also the only layer that runs before a protocol is even matched, so missed emergencies from a wrong protocol choice can't happen. The protocol conditions catch the rest.

## Two-pass red-flag: keywords before protocol, conditions after

This is the safety invariant that cost two bugs to get right. The red-flag check executes once with `protocol=None` (keyword layer only) and again after protocol matching (protocol-condition layer). In the first version, it only ran once with the matched protocol, which meant an extraction failure that produced the wrong `symptom_category` could cause the wrong protocol to be matched, which could have no red flags defined, which meant the emergency was missed entirely. The two-pass design decouples keyword detection from protocol selection. The keyword pass doesn't need a protocol, doesn't need correct extraction — it just needs the raw text string.

## `associated_symptoms contains` instead of phantom boolean fields

The protocol YAMLs originally referenced fields like `shortness_of_breath` (boolean) and `radiating_pain` (boolean) in their red-flag and disposition conditions. But `ExtractedFacts` doesn't have those as separate fields — they're entries in the `associated_symptoms` list. So `evaluate()` was always getting `None` for those fields and no condition ever matched. Fixing this meant either (A) adding every possible symptom boolean to `ExtractedFacts` and teaching the extractor to set them, or (B) changing the conditions to use `associated_symptoms contains "shortness_of_breath"`. Option B is less code, works for both LLM and heuristic extraction paths, and doesn't require changing the schema every time a new symptom is needed. Picked B.

## Heuristic fallback for extraction

When the LLM extraction call fails (times out, API error, invalid JSON), `_heuristic_fallback()` kicks in with regex and keyword maps. It infers symptom category from 6 pattern lists, parses duration with typo-tolerant regex (`3o mins` → `30 mins`), maps severity from 12+ keywords, and recognizes 7 history-flag categories from keyword matches. The alternative was to let the error propagate and return a generic "could not process" response, but that would lose the patient's message entirely. The heuristic produces the same `ExtractedFacts` shape as the LLM path — downstream components don't know or care which path was taken. Extraction quality is lower on the fallback path (no understanding of negation, no context from prior turns), but zero-data-loss is worth the trade.

## Keyword-based out-of-scope and medication classifiers

Two small lists in `state_machine.py` catch non-triage inputs before they enter the pipeline. The out-of-scope list catches diet plans, diagnosis-seeking ("do I have"), prescription management. The medication list prepends a disclaimer to GATHERING responses when patients ask about specific drugs. These are keyword substring checks, not LLM classification, for the same reason the red-flag detector is — the safety gate must work when the LLM doesn't. Both are easy to bypass with novel phrasings, and that's fine — they're a courtesy filter, not a security boundary.

## SQLite, not Postgres

Single-file SQLite for patient case persistence. Zero infrastructure, zero config, portable. The alternative (Postgres) would require a running server, connection pooling, and migration scripts — not worth it for a synthetic-data demo with a handful of concurrent conversations. The production trigger is concurrent write load: SQLite serializes writes. That's a named production gap in `PRODUCTION_READINESS.md`, not a design flaw.

## Three providers via OpenAI SDK, not LiteLLM

Primary and fallback per task across OpenRouter, NVIDIA NIM, and Google AI Studio, all accessed through the `openai` Python SDK with different `base_url` values. LiteLLM would abstract the provider switching, but it's another dependency with its own gotchas. The OpenAI SDK's drop-in compatibility across all three providers is well-tested, and the retry/fallback logic is 30 lines of Python in `llm/client.py`. Provider diversity means no single API key going down takes the whole system out — each task has a fallback on a different provider, and the fallback for one task might be the primary for another.

## Groundedness enforcement, not just prompting

The explanation generator calls the LLM, then runs `is_grounded()` — a token-allowlist check that rejects explanations mentioning symptoms that aren't in the extracted facts. If the check fails, it falls back to a deterministic template with the protocol's safety-netting text. The alternative was to trust the LLM prompt ("do not add symptoms not in the facts") alone. That would be naive — LLMs follow instructions roughly, not precisely, and an explanation that invents a symptom is actively dangerous in a triage context. The allowlist is crude (200-ish common words plus the exact fact values), but crude enforcement beats no enforcement.

## No fine-tuning, no RAG

Early in the project, the obvious "senior architect" choices were a RAG pipeline over the triage protocols, or a fine-tuned model for extraction and classification. Both are legitimate tools. Both were seriously considered — I didn't dismiss them on reflex. But I rejected both, and the reasoning wasn't about time or resources. Here's why.

**RAG fell apart on scale.** RAG earns its cost when the knowledge base is large — hundreds to thousands of documents — and retrieval needs to surface the relevant few out of many. This project has exactly 7 hand-authored protocols in a flat directory. Retrieval over 7 documents isn't retrieval, it's a lookup table wearing a vector database as a costume. Worse, RAG introduces a failure mode this project can't afford: similarity search returns the wrong protocol with high confidence scores, and a wrong protocol on a safety-critical path is strictly worse than a fallback that correctly says "I don't know what this is." A `symptom_category` key match with scoring fallback through keyword-token overlap, plus a `fallback_no_match` protocol that defaults to URGENT_CARE (and can resolve as low as PRIMARY_CARE for mild cases when severity is known) — that gets the same coverage with a failure mode that's safe by construction. I've already debugged enough phantom-boolean-field bugs to know that opacity in the safety path is the one thing I won't trade for elegance.

**Fine-tuning had the wrong data profile.** Fine-tuning needs a real labeled dataset — hundreds to thousands of clinically-reviewed examples — to produce something more reliable than a well-scoped prompt against a frontier model. This project has exactly 11 eval cases, sized for testing, not training. Fine-tuning on 11 examples doesn't improve recall, it memorizes the exact phrasings in those 11 while degrading on everything else — the exact opposite of what a safety system needs. There's also an auditability problem: "the fine-tuned model decided" is a worse incident explanation than "the extraction model read the text, RF-CARDIAC-01's condition evaluated true because duration was 30 minutes and `shortness_of_breath` was in the associated_symptoms list, so the red-flag fired." Auditability is a real requirement here, not a nice-to-have. Human-readable rule sets trace every decision to a condition a person wrote and can defend.

**The failure that cemented this.** Early versions of the protocol conditions referenced fields like `shortness_of_breath` and `radiating_pain` as booleans on `ExtractedFacts`. But those fields never existed — `ExtractedFacts` stores them in the `associated_symptoms` list. So every condition evaluated to `None`, which means false, which means red flags never fired and disposition rules never matched. The system silently under-triaged every case. Debugging that took longer than I want to admit because there was no trace — no rule output to log, no audit trail. If I can't confidently trace why a disposition decision was made, I can't fix it when it's wrong. A rule set you can dump, log, and replay beats any black-box approach for this specific problem.

**Named as future work, not attempted.** The one place a fine-tuned or distilled model would genuinely earn its place — a small local model doing extraction specifically, trained on real (properly de-identified, consented) conversation data — is noted in `PRODUCTION_READINESS.md` rather than built here. Until then, 79 trigger keywords, 7 YAML files, and a recursive `evaluate()` function. I know exactly what every one of them does.

## Out of scope, and why

- **Postgres/Redis** — SQLite is sufficient for one-process demo scale. Add Postgres when concurrent write throughput matters.
- **Kubernetes / OpenTelemetry / Grafana / Prometheus** — `structlog` structured JSON output and a single FastAPI process is enough to monitor during development. The full observability stack is premature.
- **LiteLLM or a provider-gateway service** — three providers, each on a different account, accessed via the `openai` SDK with different `base_url` values. Rolling our own fallback is 30 lines of code in `llm/client.py` and zero network hops.
- **Fine-tuning or RAG** — 7 protocols, 11 eval cases. Neither the corpus volume nor the training-data profile justifies either approach.
- **Real multi-tenant auth** — the `X-API-Key` header matches a single key from `.env`. That's a placeholder. Real auth would need JWTs, scopes, and per-tenant key rotation.
- **HIPAA compliance** — `SYNTHETIC_DATA_ONLY=true` is the non-negotiable guard. This system never touches real PHI. HIPAA BAAs, audit logging, and access controls are not implemented because they shouldn't be needed.

## Accepted trade-offs

- Disposition rules that depend on missing fields are silently skipped, not evaluated with null. This is conservative (avoids false-negative matches) but means some rules may never fire if a field is never collected.
- The extraction prompt tells the LLM to treat hedged language ("probably nothing but...") as evidence the symptom is present. This correctly handles downplayed emergencies but will capture false symptoms for genuinely worried-but-well patients. The disposition rules and red-flag detector are the second pass.
- `SYNTHETIC_DATA_ONLY=true` is a startup log warning, not a runtime-enforced lock. Nothing in the code stops a caller from sending real patient data. The `.env.example` defaults to `true` and the warning is visible on every start, but there's no gate.
- The `merged_facts()` logic resets per-turn state (`turn_count`, `questions_asked`, `matched_protocol_id`) when `symptom_category` changes between turns. This is correct for the common case (patient describes a new problem in a follow-up) but discards the entire conversation context for that patient case.
