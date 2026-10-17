# AGENTS.md — standing instructions

## PRISM tracing (do not remove)

This project sends traces to PRISM. Env vars: `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`, `PRISMTRACE_ORG_ID`, `PRISMTRACE_HOST`.

Tracing is wired at:
- `app/services/prism.py` — HTTP emitter, one trace per analysis/onboarding step
- `app/services/orchestrator.py` — 12-step analysis run (`agent_id=moneyfinder-backoffice`)
- `app/routes/flow.py` — 11-step onboarding flow
- `app/routes/api.py` — onboarding phase APIs
- `scripts/prism_smoke.py`, `scripts/prism_seed_failures.py` — connection/seed helpers

**Standing rule.** Whenever you add or change an agent, chain, graph, tool, retriever, or any entry point that calls a model, wire it to PRISM before you finish. Unwired code is invisible in the dashboard. If you are unsure whether something is covered, assume it is not and wire it.

**Current limitation (be honest about it).** The emitter sends one HTTP trace per step with a summary. It does **not** emit OpenTelemetry spans, so PRISM `spans`, `tool_calls`, and token/cost fields are empty. If a demo needs the "Steps / tool calls" view, add SDK or OTel span instrumentation and verify it in PRISM; do not claim the HTTP traces capture tool calls.
