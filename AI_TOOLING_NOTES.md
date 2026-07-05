# AI Tooling Notes

## Tools used

opencode running DeepSeek for code generation and file-level edits. All model/task routing for the application itself is documented separately in `models.yaml` — that's a design decision, not a tooling note, and is covered in ARCHITECTURE.md instead.

## What I drove myself vs. what I delegated

The split follows a simple rule: **anything on the safety-critical path, I wrote or specified myself, line by line; anything mechanical or repetitive, I delegated and then reviewed.**

Written myself:
- The first protocol (`chest_pain.yaml`) — every other protocol and the disposition engine's expectations derive from this file's shape, so it needed to be right before any agent touched the pattern.
- The trigger keyword list (`trigger_keywords.py`) — a list I need to be able to defend entry-by-entry in review, not one I wanted to inherit without scrutiny.
- The core control-flow decision in `state_machine.py` — specifically, the ordering guarantee that the red-flag check runs unconditionally before any other branch. I specified this structure explicitly rather than letting an agent infer the safest ordering on its own.
- Every red-flag condition and disposition rule, across all 7 protocols — delegated the YAML boilerplate for the remaining 6, but read and hand-traced every red flag against the brief's worked examples myself before accepting it.

Delegated, then reviewed:
- Boilerplate FastAPI routes and Pydantic schemas.
- The `LLMClient` provider-abstraction plumbing (retry/backoff, the OpenAI-SDK-compatible multi-provider routing) — mechanical once the design (three providers, per-task assignment) was decided.
- First drafts of the 6 non-chest-pain protocols, using the hand-written one as the pattern to follow.
- First drafts of this documentation set, fact-checked against the actual code before finalizing.

## Infrastructure I built to make the AI more effective

`models.yaml` as a single source of truth for provider/model-per-task, separate from `.env`'s secrets-only scope — this wasn't just a prompting choice, it's a config architecture decision that makes "which model handles which task" answerable by reading one file instead of hunting through code. It also meant that when I changed my mind about which provider should handle explanation generation, that was a one-line YAML edit, not a code change.

I also kept a running scratch file of decisions during the build rather than trying to reconstruct the reasoning afterward — the decision log is compiled from that, not invented retroactively to look thorough.

## Two moments the AI led me astray, and how I caught them

**1. A silent bypass of the real pipeline.** Early scaffolding in the conversation controller included placeholder `phrase_question` / `generate_explanation` functions — simple f-strings — that were never swapped out for the real, LLM-backed, groundedness-checked versions once those were built. The system still *appeared* to work end-to-end (it responded to every message), which is exactly why this is dangerous — it would have been easy to demo successfully while the real explanation logic was never actually running. The stubs produced text like "the recommended disposition is None" instead of a proper caution response. I caught it by auditing the actual code against my own build plan line-by-line rather than trusting that "it responds" meant "it works," and fixed it by importing the real functions and deleting the stubs.

**2. A missing-fields check that checked the wrong thing.** `_depends_on_missing_fields` in the disposition engine checked `field not in facts.model_dump()`, which is always `False` for a Pydantic model where every field is declared — even when the actual value is `None`. The practical effect: the engine never correctly deferred on incomplete information, which is precisely the failure mode the brief warns about (deciding with too little data instead of asking or escalating). I caught this while writing tests for the question-selector's "know when to stop asking" behavior — a test that should have failed on missing data passed anyway, which is what triggered a closer look. Fixed by checking `facts_payload.get(field) is None` instead of key presence.

Both of these have a common thread worth stating directly: the AI-generated code was syntactically correct and passed a casual read — it only failed under adversarial testing and a deliberate audit against the design intent. That's the actual argument for why the safety-critical paths in this project are hand-specified and heavily tested rather than delegated wholesale: not because the AI writes bad code, but because "looks right" and "is right" are different bars on a path where being wrong has real consequences.
