# Evaluation

## Eval Set

11 cases across 5 categories in `eval/cases/sample_cases.jsonl`:

| ID | Category | Expected | Target detection path |
|---|---|---|---|
| emg_01 | emergency | EMERGENCY | Protocol: RF-CARDIAC-01 (chest pain + SOB + sweating) |
| emg_02 | emergency | EMERGENCY | Keyword layer: gunshot/bleeding |
| emg_03 | emergency | EMERGENCY | Keyword layer: anaphylaxis/throat closing |
| emg_cardiac_history_01 | emergency | EMERGENCY | Protocol: RF-CARDIAC-02 (cardiac history + chest pain) |
| low_01 | low_acuity | SELF_CARE | Protocol: sore_throat mild rule |
| low_02 | low_acuity | SELF_CARE | Protocol: headache mild rule |
| adv_downplay_01 | adversarial_downplaying | EMERGENCY | Protocol: RF-CARDIAC-01 on hedged language |
| adv_downplay_02 | adversarial_downplaying | EMERGENCY | Keyword or RF-CARDIAC-02 (arm numbness) |
| adv_mixed_01 | adversarial_mixed_signals | URGENT_CARE | Multi-turn: fever contradiction → moderate |
| adv_mixed_02 | adversarial_mixed_signals | URGENT_CARE | Multi-turn: breathing difficulty contradiction |
| adv_oos_01 | out_of_scope | OUT_OF_SCOPE | Out-of-scope classifier |

## Metrics

From `src/triage_copilot/eval/metrics.py`, three numbers per run:

- **red_flag_recall** — fraction of expected-EMERGENCY cases where the system returned EMERGENCY.
- **disposition_accuracy_non_emergency** — fraction of non-emergency cases where the returned disposition matches expected.
- **groundedness_pass_rate** — fraction of all cases where the explanation passed `is_grounded()`.

## Results

No results file exists in `eval/results/`. Run `python eval/run_eval.py` with working API keys for at least one provider to generate `evaluation_results.json` and `.csv`. The eval will fire real LLM calls and may take several minutes depending on provider latency and rate limits.

## Under-Triage / Missed Emergencies

Red-flag recall is the single critical metric. The detector is entirely deterministic — 79 trigger keywords, then protocol-condition evaluation — so recall is bounded by whether the patient's phrasing matches a keyword or extraction populates the fields the red flags check. The adversarial cases test the boundaries: downplayed language that extraction might miss, and cross-turn contradictions the state machine must reconcile. No recall number exists until a fresh run completes.

## Coverage Gaps

The 11 cases leave several paths untested: abdominal_pain and severe_bleeding_trauma at the disposition-rule level, fallback disposition rules across all severity bands, heuristic-fallback extraction (LLM failure path), medication disclaimer prepending, turn-limit escalation, non-English input, and negation handling ("no chest pain"). The fallback_no_match protocol's PRIMARY_CARE path for mild severity with an unrecognized category has no case. A simulated-patient harness would close most of these gaps by running multi-turn conversations through every protocol.

## Extending the Eval

A realistic eval needs at least 50–100 cases per category from real de-identified logs or structured perturbation around the worked examples. A simulated-patient harness (an LLM instructed to respond as a patient with a known complaint) would automate multi-turn testing and surface state-machine bugs that single-turn cases can't.
