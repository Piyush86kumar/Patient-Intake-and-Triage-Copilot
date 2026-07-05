# AI Tooling Notes — Triage Copilot

## Moments where the agent's output required human correction

### Condition evaluation: agent initially used eval()-able expression strings
In Step 3, when generating `guidance/schema.py`, the agent's first attempt represented conditions as raw Python-expression strings (e.g., `"duration_minutes < 60"`) intended to be fed to `eval()`. This was caught during review — the BUILD_GUIDE explicitly says "never let a config file contain executable code." The structured `{field, op, value}` / `{all, any}` recursive model was written manually to replace it, and `eval(` / `exec(` were banned via a repo-wide search.

### Trigger keyword list: agent trimmed the list
In Step 4, the agent's initial `trigger_keywords.py` contained only ~15 entries (the short list from Step 4's first code block in the BUILD_GUIDE). The expanded list (~50+ entries) from later in Step 4 had to be added manually. The audit confirmed the full list is now present.

### Protocol YAML: agent omitted fallback_no_match
The agent generated all 5 remaining protocol YAML files but initially skipped `fallback_no_match.yaml`. This was caught because the BUILD_GUIDE explicitly lists it and notes it's "the actual mechanism for handling the N-scenario problem." Added manually.

### Controller stubs: agent left local overrides in state_machine.py
The `state_machine.py` had inline `phrase_question` and `generate_explanation` stubs that shadowed the real implementations in `questioning/` and `explanation/`. These were caught during the audit (Step 10 critical finding) — they caused all conversations to use hardcoded template text instead of LLM-generated responses, and directly caused 20%/0%/0% eval scores. Fixed by deleting the local stubs and importing the real functions.

### The disposition=None crash path was present from the start
The `decide_disposition()` function could return `disposition=None`, but `process_turn()` passed it to `generate_explanation()` without a guard. This produced `"the recommended disposition is None"` for inputs where no disposition rule matched. The audit flagged this as the known crash bug; a None-disposition guard was added.

## What the agent did well

- Generated the configuration loader (`config.py`) with clean separation of `Settings` (pydantic-settings) and `ModelRegistry` (YAML) — this matched the spec exactly on first pass.
- Generated the protocol YAML files with the correct nested condition structure after the initial schema was provided.
- Produced working FastAPI endpoint implementations for all three required routes.
- The Recursive `Condition` model's `model_validator` correctly rejects mixed leaf/composite shapes.

## What required the most manual verification

1. **The order of operations in `process_turn()`** — ensuring `check_red_flags()` runs unconditionally before any disposition logic. This was checked by reading the actual control flow line by line, not by trusting the architecture diagram.
2. **The eval cases (`eval/cases/sample_cases.jsonl`)** — hand-written manually to match the 10-case set from the brief, including two multi-turn cases (`adv_mixed_01`, `adv_mixed_02`).
3. **The `is_grounded()` function** — the initial version was too permissive (accepting any text that didn't contain specific disallowed words). Rewritten to a positive check: every content token in the explanation must appear in the extracted facts.
