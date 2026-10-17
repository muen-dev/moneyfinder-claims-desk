# AGENTS.md — standing instructions

## PRISM tracing (do not remove)

This project sends traces to PRISM. Env vars: `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`, `PRISMTRACE_ORG_ID`, `PRISMTRACE_HOST`.

Tracing is wired at:
- `app/services/prism.py` — HTTP emitter, one trace per analysis/onboarding step
- `app/services/tracing.py` — OpenTelemetry spans → PRISM (`/api/spans/ingest`)
- `app/services/orchestrator.py` — 12-step analysis run (`agent_id=moneyfinder-backoffice`)
- `app/routes/flow.py` — 11-step onboarding flow
- `app/routes/api.py` — onboarding phase APIs
- `scripts/prism_smoke.py`, `scripts/prism_seed_failures.py` — connection/seed helpers

**Standing rule.** Whenever you add or change an agent, chain, graph, tool, retriever, or any entry point that calls a model, wire it to PRISM before you finish. Unwired code is invisible in the dashboard. If you are unsure whether something is covered, assume it is not and wire it.

**Instrumentation status.** Tool/model spans are wired through `app/services/tracing.py` using the PRISM SDK OpenTelemetry exporter (`/api/spans/ingest`); `app/services/prism.py` remains the HTTP fallback for environments without the SDK. An analysis run emits one agent span + 12 tool spans + 1 LLM span with token usage; verify with `GET /api/spans/{trace_id}` after a run. Onboarding emits one tool span per phase step. If PRISM evaluation is enabled, also confirm the project eval-config has a valid key; an unset eval key makes traces look flagged even when the app is healthy.
