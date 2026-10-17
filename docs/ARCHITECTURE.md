# Architecture — what powers what

**Short answer: PRISM is not the backend.** PRISM is an observability/test platform that the backend *sends traces to*. The backend is a Flask (Python) app. Nicrron is the model provider the backend *calls*. Data lives in local fixtures and a JSON state file.

```
                    ┌─────────────────────────────────────────────┐
                    │ Browser / team / judge                      │
                    │  server-rendered Jinja pages + JSON fetches │
                    └───────────────────┬─────────────────────────┘
                                        │ HTTP
                    ┌───────────────────▼─────────────────────────┐
                    │ Flask backend  (app/)                       │
                    │  routes/ → services/ → store.py              │
                    │                                             │
                    │  fixtures/*.json   demo source of truth      │
                    │  data/state.json   runtime events + runs     │
                    └───────┬───────────────────────┬─────────────┘
                            │ model call            │ trace per step
                    ┌───────▼─────────┐     ┌───────▼────────────────┐
                    │ Nicrron API     │     │ PRISM ingest            │
                    │ api.nicrron.ai  │     │ api.prism.blockconvey   │
                    │ OpenAI-compat   │     │ observability only      │
                    │ (LLM inference) │     │ (no business data)      │
                    └─────────────────┘     └────────────────────────┘
```

## The four layers

| Layer | What it is | What it does | What it does **not** do |
|---|---|---|---|
| **Frontend** | Flask + Jinja templates + one CSS file | Dashboard, onboarding, eligibility, books, run history, settings; forms POST back | No React/SPA; no client-side database |
| **Backend** | Python Flask app in `app/` | Business logic: profile facts, eligibility verdicts, status machine, money math, packet generation, API | No PRISM dependency; no external database |
| **Nicrron** | OpenAI-compatible model gateway | One real model call in `eligibility_extract`; can be used for more steps | It is not a database, backend or orchestrator |
| **PRISM** | LLM observability + failure detection | Receives one trace per analysis step; shows sessions, steps, alerts, root-cause clusters | It does not serve pages, store business data, or run the agent |

**Analogy:** the Flask app is the restaurant kitchen. Nicrron is a supplier that delivers ingredients (model output). PRISM is the security camera and health inspector that records what happened — if the camera is off, the kitchen still cooks, but you lose the evidence.

## Request flows

### 1. Page load
`GET /dashboard` → Flask route → `store.py` loads `fixtures/` → Jinja renders HTML → browser.
No PRISM, no Nicrron, no network required.

### 2. Run analysis (`POST /api/analysis/run`)
1. Flask creates a `run_id` (also the PRISM session id).
2. The 12-step orchestrator executes deterministic services (inbox scan, ledger reconciliation, program matching, packet build).
3. `eligibility_extract` calls **Nicrron** (`nicrron/auto`) with a strict-JSON prompt; the result is stored on the run.
4. After each step, the backend POSTs one trace to **PRISM** (`/api/traces`) with `session_id`, `agent_id=moneyfinder-backoffice`, step/tool/status.
5. The run (steps, latency, errors, telemetry status) is written to `data/state.json` and shown on `/run-history`.
6. If PRISM is unreachable, the run still completes and telemetry is marked `pending`; the UI never shows a fake PRISM link.

### 3. Accountant packet (`POST /api/ledger/packet`)
Flask reads the ledger fixture, computes totals in integer cents in code, writes Markdown + CSV + XLSX under `data/packets/`, and returns real download links. No model is involved in the arithmetic.

## Failure behavior (by design)

| Failure | What happens |
|---|---|
| PRISM down/unconfigured | App works; run `telemetry: pending`; Settings shows `configured`/`unavailable`; no fabricated proof |
| Nicrron down | The `eligibility_extract` step fails; run becomes `partial`; evidence already collected is kept |
| Fixture missing | Page shows an explicit empty/error state; no invented data |
| Illegal status transition | API returns `400 invalid_transition`; UI shows the error |

## Where the data lives

- **Demo dataset:** `fixtures/*.json` — synthetic Gowanus Kettle business, inbox, applications, programs, ledger, runs.
- **Runtime state:** `data/state.json` (gitignored) — events, runs, resets. `data/packets/` — generated packet files.
- **Secrets:** `.env` (gitignored); `.env.example` names only.
- **No external database** in this scaffold. SurrealDB was in the prior build; it is not required here.

## What PRISM actually buys us

- **Sessions / Steps:** one run = one trajectory with 12 named tool steps. This is the hackathon's Money Operations proof #1.
- **Alerts:** a rule can fire on failed traces or partial runs (Money Operations proof #2).
- **Root Cause:** clusters of failed runs and their cause; then v2 passes the same inputs (proof #3).
- **Run history:** honest local steps vs verified PRISM link.

PRISM is required by the event, so the app emits to it on every real run — but the app is intentionally designed to degrade gracefully without it.

## Sharing

- **Stable code link:** https://github.com/muen-dev/moneyfinder-claims-desk
- **Live demo:** local `http://127.0.0.1:8000`, or a temporary `cloudflared` tunnel for the team. The tunnel URL is not committed because it expires.
- **Run locally:** `make setup && make run` (see README).
