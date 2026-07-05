# Audit Differences Report — Triage Copilot vs BUILD_GUIDE.md Specification

**Audit date:** 2026-07-05
**Specification:** `BUILD_GUIDE (1).md` (857 lines)
**Implementation:** Current repository state

---

## Step-by-step analysis

### Step 0 — Scaffolding

| Item | Spec Says | Actual | Difference |
|------|-----------|--------|------------|
| `.python-version` | Should exist (Python 3.13+) | **MISSING** | No `.python-version` file; `pyproject.toml` also lacks `requires-python` constraint |
| `protocols/SOURCES.md` | Listed in project structure | **MISSING** | File does not exist |
| `api/schemas.py` | Listed as separate file | **PARTIAL** | Response models defined inline in `api/main.py` instead of separate `schemas.py` |
| `eval/cases/emergencies.jsonl` | Separate files per category | **DONE DIFFERENTLY** | Single `eval/cases/sample_cases.jsonl` with all 10 cases (functionally equivalent) |
| `eval/cases/low_acuity.jsonl` | Listed in spec | **MISSING** | Combined into single file |
| `eval/cases/adversarial_downplaying.jsonl` | Listed in spec | **MISSING** | Combined into single file |
| `eval/cases/adversarial_mixed_signals.jsonl` | Listed in spec | **MISSING** | Combined into single file |
| `eval/cases/out_of_scope.jsonl` | Listed in spec | **MISSING** | Combined into single file |
| `eval/metrics.py` | Spec says at `eval/metrics.py` | **DONE DIFFERENTLY** | Located at `src/triage_copilot/eval/metrics.py` instead |
| `logging/logger.py` | Listed as `logging/logger.py` | **DONE DIFFERENTLY** | Logger is in `logging/__init__.py` (no separate `logger.py`) |
| `data/triage.db` | Spec says `triage.db` | **DONE DIFFERENTLY** | Code uses `patient_cases.db` |
| `Dockerfile` | Listed in project structure | **MISSING** | No Dockerfile exists |
| `docker-compose.yml` | Listed as optional | **MISSING** | No docker-compose.yml exists |
| `ARCHITECTURE.md` | Listed as deliverable | **MISSING** | Does not exist |
| `DECISION_LOG.md` | Listed as deliverable | **MISSING** | Does not exist |
| `PRODUCTION_READINESS.md` | Listed as deliverable | **MISSING** | Does not exist |
| `AI_TOOLING_NOTES.md` | Listed as deliverable | **MISSING** | Does not exist |
| `eval/run_eval.py` location | Spec says `eval/run_eval.py` | **PARTIAL** | `eval/run_eval.py` exists but imports `triage_copilot.eval.metrics` (packaged version under `src/`) instead of a sibling `eval/metrics.py` |
| `.gitignore` excludes `.venv/`, `__pycache__/`, `*.db`, `.env` | Spec lists 5 patterns | **PARTIAL** | `.gitignore` has extra entries not in spec: `STATUS_UPDATE.md`, `MASTER_AUDIT_PROMPT.md`, `BUILD_GUIDE (1).md`. Missing `eval/results/*.json` from the spec's original list (spec says to include it in the cat command, but actually it IS in the gitignore). Extra `*.pyc` is present (reasonable addition). |
| `tests/integration/` | Spec shows `test_full_conversation_flow.py` | **MISSING** | `tests/integration/` directory is empty |
| `eval/case/` (singular) | Not in spec | **EXTRA** | Empty directory `eval/case/` exists (likely a typo/mistake) |
| `sitecustomize.py` | Not in spec | **EXTRA** | Adds `src/` to `sys.path` — harmless helper |
| `triage_copilot/__init__.py` (top-level) | Not in spec | **EXTRA** | Namespace shim for `uvicorn --reload` — harmless but unplanned |
| Extra test files | Not in spec | **EXTRA** | `test_config.py`, `test_schema_models.py`, `test_eval_metrics.py`, `test_fact_extractor_fallback.py` — beneficial additions |
| `pytest.ini` | Not in spec | **EXTRA** | Sets `pythonpath = src` — harmless |

### Step 1 — Config loader

| Check | Status | Details |
|-------|--------|---------|
| `config.py` loads `.env` via `pydantic-settings` | **DONE** | `Settings` class uses `SettingsConfigDict` with `env_file` |
| `config.py` loads `models.yaml` via `ModelRegistry` | **DONE** | `ModelRegistry._load_models()` reads YAML, resolves providers |
| Two separate concerns | **DONE** | Settings and ModelRegistry are separate classes |
| Fails fast at import time if required env var missing | **DONE** | `_build_settings()` wraps `Settings()` in try/except, re-raises as `RuntimeError` |
| Fails fast if `models.yaml` missing/bad | **DONE** | `_load_models()` raises on missing file, missing providers, bad entries |
| `SYNTHETIC_DATA_ONLY` wired to anything | **MISSING** | Flag is loaded into `Settings` but never read/used anywhere in the codebase |

### Step 2 — chest_pain.yaml

| Check | Status | Details |
|-------|--------|---------|
| File exists | **DONE** | `protocols/chest_pain.yaml` |
| Uses nested `{field, op, value}` / `{all/any}` shape | **DONE** | Matches spec exactly |
| Hand-trace: "crushing chest pain 30 min, short of breath, sweaty" | **DONE** | `duration_minutes=30 < 60` ✓, `shortness_of_breath=true` ✓ → fires RF-CARDIAC-01 → EMERGENCY |

### Step 3 — Pydantic schemas + condition evaluator

| Check | Status | Details |
|-------|--------|---------|
| `guidance/schema.py` exists with Condition, RedFlag, DispositionRule, Protocol | **DONE** | All four models defined |
| `extraction/schema.py` exists with ExtractedFacts | **DONE** | All specified fields present |
| `evaluate()` exists and avoids `eval()`/`exec()` | **DONE** | Pure recursive function with operator dispatch; no `eval(` or `exec(` anywhere in repo |
| `test_condition_evaluation_matches_hand_trace` exists | **PARTIAL** | Test exists but **has a broken import** (`load_protocol` doesn't exist in `protocol_store.py`). Cannot run. |

### Step 4 — Remaining protocols + trigger keywords

| Check | Status | Details |
|-------|--------|---------|
| All 7 protocol YAML files exist | **DONE** | 7 files present (chest_pain, shortness_of_breath, severe_bleeding_trauma, sore_throat, abdominal_pain, headache, fallback_no_match) |
| Each has `required_fields` | **DONE** | All 7 have required_fields |
| Each has at least one `red_flags` entry (except fallback) | **DONE** | 6 protocols have red_flags; fallback has empty red_flags |
| Each has `disposition_rules` | **DONE** | All 7 have disposition_rules |
| `fallback_no_match.yaml` defaults to `URGENT_CARE` | **DONE** | Single default rule → `URGENT_CARE` |
| Trigger keywords match the expanded list | **DONE** | Full 50+ entry list is present in `trigger_keywords.py` — includes all entries from the spec's Step 4 expanded list (shot, gunshot, gsw, stabbed, stabbing, etc.) |

### Step 5 — Red-flag detector

| Check | Status | Details |
|-------|--------|---------|
| `check_red_flags()` checks raw text against trigger keywords | **DONE** | Layer 1: `check_trigger_keywords(raw_text)` |
| `check_red_flags()` evaluates protocol-level red flags | **DONE** | Layer 2: iterates `protocol.red_flags` using `evaluate()` |
| Two distinct checks | **DONE** | Keyword check short-circuits before protocol rules |
| Test for downplayed/hedged language | **MISSING** | No test covering `test_downplayed_language_still_extracts_and_fires` (named in spec) or similar |
| Test for raw-text trigger case | **PARTIAL** | `test_keyword_trigger_short_circuits_before_protocol_rules` covers this but not named as spec requests |
| Test for clearly-negative case | **DONE** | `test_returns_not_fired_when_no_conditions_match` covers this |
| Test names match spec function names | **PARTIAL** | Tests are named differently than the spec's examples (`test_chest_pain_with_dyspnea_fires_emergency`, etc.) |

### Step 6 — Disposition engine

| Check | Status | Details |
|-------|--------|---------|
| `decide_disposition()` evaluates rules in order | **DONE** | Iterates `protocol.disposition_rules` in definition order |
| Returns first matching rule | **DONE** | Returns immediately on first `evaluate()`-true rule |
| Returns `None` when required facts missing | **PARTIAL** | `_depends_on_missing_fields()` checks field existence in `model_dump()` keys — but since ExtractedFacts has all fields defined, this **never returns True** for defined fields. Missing/null values (e.g., `severity=None`) are NOT detected as missing. The function only returns `None` when no rules match at all, which can happen but is not the same as the spec's intent. |

**Issue:** `_depends_on_missing_fields` at `disposition_engine.py:29-38` checks `condition.field not in facts.model_dump()` — this checks if the field name exists in the model's keys, not if its value is present/non-null. Since all ExtractedFacts fields are always present in `model_dump()`, this virtually never triggers.

### Step 7 — Guidance matcher + question selector

| Check | Status | Details |
|-------|--------|---------|
| `match_protocol()` falls back to `fallback_no_match.yaml` | **DONE** | Returns fallback protocol when no match found |
| `match_protocol()` never returns `None` | **DONE** | Always returns a Protocol (raises only if no fallback available) |
| `next_missing_field()` returns `None` when all fields present | **DONE** | Returns `None` when all required fields have non-null values |
| `test_unmatched_symptom_falls_back_to_caution_protocol` exists | **DONE** | Named `test_match_protocol_falls_back_to_no_match_protocol` but functionally identical |

### Step 8 — Multi-provider LLM client

| Check | Status | Details |
|-------|--------|---------|
| Implements retry-then-fallback across primary/fallback | **DONE** | Retries `LLM_MAX_RETRIES` times per provider, then falls to next |
| Validates output against Pydantic model before returning | **DONE** | `response_model.model_validate_json(content)` on every code path |
| Evidence of fallback testing | **MISSING** | No log files, comments, or test notes showing fallback was actually tested with real API keys |

### Step 9 — Fact extractor

| Check | Status | Details |
|-------|--------|---------|
| Extraction prompt instructs model to treat hedged language as present | **DONE** | `prompts.py` line 31: "Treat hedged or minimizing language... as evidence that the symptom is PRESENT" |
| Downplaying manual test evidence | **MISSING** | No script, log, or comment evidence that `"probably nothing but..."` was run against a real model |

### Step 10 — Conversation controller — **CRITICAL**

| Check | Status | Details |
|-------|--------|---------|
| `check_red_flags()` called after every fact merge, on every turn, unconditionally | **DONE** | `state_machine.py:70` — called unconditionally after `merge_facts()` |
| `check_red_flags()` called strictly before `match_protocol()` | **DONE** | Red-flag check at line 70-74; protocol matching at line 81 |
| `disposition_result is None` check before explanation generator | **NOT FIXED** | Line 92-93: `disposition_result = decide_disposition(...)` then immediately `await generate_explanation(disposition_result, ...)` — **no None check**. If `disposition_result.disposition` is None, state_machine's local `generate_explanation` (line 61-62) produces: `"Based on the information provided, the recommended disposition is None."` |

**CRITICAL FINDING:** The `state_machine.py` has its own local stub implementations that **completely bypass** the real modules:
- `phrase_question` (line 57-58): Returns `f"Can you tell me about {field}?"` instead of calling `questioning/question_selector.py`'s LLM-powered version
- `generate_explanation` (line 61-62): Returns `f"Based on the information provided, the recommended disposition is {disposition_result.disposition}."` instead of calling `explanation/explanation_generator.py`'s LLM-powered version with groundedness check

This means the entire LLM-powered question phrasing and explanation generation pipeline is **unused in the actual conversation flow**. All conversations get templated text, not LLM-generated responses.

| `MAX_QUESTIONS_PER_CONVERSATION` enforced | **DONE** | Line 76: `if case.turn_count >= settings.MAX_QUESTIONS_PER_CONVERSATION` |

### Step 11 — Question phrasing + explanation generation

| Check | Status | Details |
|-------|--------|---------|
| `generate_explanation()` includes groundedness check | **DONE** | `explanation_generator.py:64` calls `is_grounded()` |
| Fallback template path exists | **DONE** | `fallback_template_explanation()` at line 28-32 |
| `phrase_question()` exists in question_selector | **DONE** | `question_selector.py:30-33` |

But as noted in Step 10, **neither is actually called by the controller** — the controller uses its own local stubs.

### Step 12 — API, CLI, Gradio UI

| Check | Status | Details |
|-------|--------|---------|
| `POST /conversations` exists | **DONE** | `api/main.py:44` |
| `POST /conversations/{id}/messages` exists | **DONE** | `api/main.py:53` |
| `GET /conversations/{id}/state` exists | **DONE** | `api/main.py:64` |
| CLI calls `process_turn()` directly (in-process) | **DONE** | `cli/chat.py:30` — calls `process_turn()` directly, no HTTP |
| Gradio calls `process_turn()` directly (in-process) | **DONE** | `ui/gradio_app.py:9` — calls `process_turn()` directly |
| Gradio "Clinician View" tab renders real state | **DONE** | Calls `PatientCase.load()` and displays `model_dump()` |
| Gradio mounted inside FastAPI | **NOT DONE** | Gradio is standalone (`__main__` launch), NOT mounted via `gr.mount_gradio_app()` |
| `api/schemas.py` as separate file | **MISSING** | Schemas inline in `api/main.py` |

### Step 13 — Eval harness

| Check | Status | Details |
|-------|--------|---------|
| Case files exist under `eval/cases/` | **DONE** | `eval/cases/sample_cases.jsonl` with 10 cases |
| All 10 required case IDs present | **DONE** | `emg_01`, `emg_02`, `emg_03`, `low_01`, `low_02`, `adv_downplay_01`, `adv_downplay_02`, `adv_mixed_01`, `adv_mixed_02`, `adv_oos_01` — all present |
| Multi-turn `"turns"` field supported | **DONE** | `run_eval.py:37` loads `case.get("turns")` and iterates |
| Actual eval results | **DONE** | See eval run results below |

**Eval results (from `eval/results/evaluation_results.json`):**
- Red-flag recall: **20%** (only 1/5 emergencies caught)
- Disposition accuracy (non-emergency): **0%** (0/5)
- Groundedness pass rate: **0%**
- Root cause: The controller's stub `phrase_question` always asks for more info instead of reaching a disposition. Only cases caught by raw-text trigger keywords (e.g., "shot") get EMERGENCY.

### Step 14 — Docker, README, writeups

| Deliverable | Status | Details |
|-------------|--------|---------|
| `Dockerfile` | **MISSING** | Not present |
| `docker-compose.yml` | **MISSING** | Not present |
| `ARCHITECTURE.md` | **MISSING** | Not present |
| `DECISION_LOG.md` | **MISSING** | Not present |
| `PRODUCTION_READINESS.md` | **MISSING** | Not present |
| `AI_TOOLING_NOTES.md` | **MISSING** | Not present |
| `README.md` | **DONE** | Present, covers CLI/API/test/eval usage |

---

## Known Issues Verification

### 1. Disposition=None crash bug — **NOT FIXED**

From `state_machine.py:92-93`:
```python
disposition_result = decide_disposition(case.facts, protocol)
explanation = await generate_explanation(disposition_result, case.facts, protocol)
```

With the local stub at line 61-62:
```python
async def generate_explanation(disposition_result, facts, protocol) -> str:
    return f"Based on the information provided, the recommended disposition is {disposition_result.disposition}."
```

If `decide_disposition()` returns `disposition=None`, the message reads "the recommended disposition is None". No guard exists.

Additionally, `_depends_on_missing_fields()` at `disposition_engine.py:38` is broken — it checks `condition.field not in facts.model_dump()` (key existence) instead of checking for null/missing values. This means rules are never treated as "depending on missing fields" for defined fields, preventing the deferral mechanism from working correctly.

### 2. Trigger keyword expansion — **PRESENT**

The expanded keyword list from the most recent Step 4 spec is fully present in `trigger_keywords.py` including all breathing variants, consciousness/neuro terms, bleeding terms, allergic/toxic terms, and other acute terms.

---

## Scope Creep / Extra Unplanned Work

| Item | Judgment | Reason |
|------|----------|--------|
| `sitecustomize.py` | Harmless | Adds `src/` to path for development convenience |
| `triage_copilot/__init__.py` (top-level) | Harmless | Namespace shim for `uvicorn --reload` subprocess support |
| `eval/case/` (empty dir) | Harmless | Likely typo of `eval/cases/` |
| Extra test files | Beneficial | `test_config.py`, `test_schema_models.py`, `test_eval_metrics.py`, `test_fact_extractor_fallback.py` — all provide additional coverage |
| `pytest.ini` | Harmless | Convenience config setting `pythonpath = src` |

No infrastructure scope creep found (no CI workflows, no extra Docker services, no complex DB schemas beyond PatientCase).

---

## Summary of Critical Findings

1. **Controller bypasses LLM modules** — `state_machine.py` has local stubs for `phrase_question` and `generate_explanation` that never call the actual implementations in `questioning/` and `explanation/`. All conversations get templated text.

2. **disposition=None unguarded** — No check before passing `disposition_result.disposition` (which can be `None`) to the explanation generator. The known crash bug remains.

3. **`_depends_on_missing_fields` is broken** — Checks field key existence instead of value presence; never detects missing data for defined fields.

4. **Eval results show 20% red-flag recall, 0% disposition accuracy** — The system fundamentally cannot reach disposition decisions because the controller stubs always ask another question instead.

5. **5 of 8 graded deliverables missing** — No Dockerfile, ARCHITECTURE.md, DECISION_LOG.md, PRODUCTION_READINESS.md, or AI_TOOLING_NOTES.md.

6. **`test_condition_evaluation_matches_hand_trace` has broken import** — References `load_protocol()` which doesn't exist.
