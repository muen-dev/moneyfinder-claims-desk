# Interface Contract — Claims Desk

Frozen for parallel work. Any shape change goes in the team thread first.

## Conventions

- JSON, `synthetic: true` in demo mode.
- Money in integer cents. `direction` is explicit: `purchase` | `credit`.
- No endpoint sends email, writes Gmail, files, modifies transactions or submits to a third party.
- Every status response includes `column` from the map below.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{ok, mode, business}` |
| POST | `/api/demo/reset` | `{ok, reset_at}` |
| GET | `/api/profile` | `{business, facts[], conflicts[]}` |
| GET | `/api/inbox?q=&category=` | `{messages[]}` |
| GET | `/api/messages/<id>` | `{message}` |
| GET | `/api/applications` | `{applications:{found[],in_process[],approved[],paid[],closed[]}, totals, count}` |
| GET | `/api/applications/<id>` | `{application, events[]}` |
| POST | `/api/applications/<id>/transition` | `{to_status, actor, note}` → `{application}`; `400 invalid_transition` |
| GET | `/api/eligibility` | `{programs[], counts, total}` |
| GET | `/api/ledger` | `{summary, transactions[], exceptions}` |
| GET | `/api/ledger/exceptions` | `{missing_receipts[], duplicates[], delta_cents}` |
| POST | `/api/ledger/packet` | `{packet, markdown}` |
| GET | `/api/ledger/packet/<packet>/<file>` | file download |
| POST | `/api/analysis/run` | `{run}` |
| GET | `/api/runs` | `{runs[]}` |
| GET | `/api/runs/<id>` | `{run}` |
| GET | `/api/integrations/status` | `{integrations[]}` |
| GET | `/api/voice/summary` | `{text, totals}` |

## Statuses

```
MATCH_FOUND · FORM_READY · USER_APPROVED · SUBMITTED · CLAIM_RECEIVED · PROCESSING
NEEDS_DOCS · APPROVED · PAYMENT_ISSUED · PAYMENT_CONFIRMED · REJECTED · STOPPED_BY_USER
```

| Column | Statuses |
|---|---|
| found | MATCH_FOUND, FORM_READY |
| in_process | USER_APPROVED, SUBMITTED, CLAIM_RECEIVED, PROCESSING, NEEDS_DOCS |
| approved | APPROVED |
| paid | PAYMENT_ISSUED, PAYMENT_CONFIRMED |
| closed | REJECTED, STOPPED_BY_USER |

Transitions are enforced in `app/services/applications.py`; `PAYMENT_CONFIRMED` only from `PAYMENT_ISSUED` and only via `store.confirm_deposit()`.

## Key shapes

```json
Application: {id, program_id, program, form, agency, amount_estimate_cents, amount_type,
  status, column, next_action, deadline, expected_by, confidence, source_url, evidence[]}
Evidence: {kind, ref, excerpt}
Program: {id, name, form, agency, jurisdiction, url, verdict, reasons[], questions[],
  source_excerpt, as_of, status, confidence}
Transaction: {id, date, vendor, description, amount_cents, direction, category,
  tax_treatment, payment_source, source_message_id, source_quote, confidence,
  needs_receipt, duplicate_of, status}
Run: {id, version, status, started_at, ended_at, steps[], telemetry, prism_session_id,
  prism_url, error, awaiting_approval, summary}
Step: {step, tool, status, latency_ms, input_summary, output_summary, error, prism_delivered}
Packet: {id, year, generated_at, files[], open_questions[], markdown, status, disclaimer}
```

## Run steps (12, one PRISM session)

`gmail_scan → extract_facts → extract_purchases → categorize_ledger → reconcile_ledger → program_candidates → agency_fetch → eligibility_extract → match_score → form_prep → human_approve → build_accountant_packet`

Tool names: `scan_inbox`, `extract_facts`, `extract_purchases`, `categorize_ledger`, `reconcile_ledger`, `find_candidates`, `fetch_program_page`, `extract_eligibility`, `score_match`, `prepare_application`, `request_approval`, `build_accountant_packet`.

## PRISM emitter

`app/services/prism.py`: one `POST /api/traces` per step, header `X-PRISMtrace-Key`, `session_id` = run id, `agent_id=moneyfinder-backoffice`. No key → `telemetry: pending`; delivery failure → `pending` with the error surfaced in Settings. Never fake a link.

## Files and ownership

| Owner | Paths |
|---|---|
| Thuy | `app/templates/base|onboarding|dashboard|eligibility|books`, `app/static/css/app.css`, `docs/proofs/**` |
| Kenan | `app/templates/index|application|run_history|settings`, `app/static/js/**`, demo video |
| Richard | `app/routes/**`, `app/services/**`, `app/store.py`, `fixtures/**`, `scripts/**`, tests |

## Env

```bash
DEMO_MODE=true
NICRRON_API_KEY=            # required sponsor
NICRRON_BASE_URL=https://api.nicrron.ai/v1
NICRRON_MODEL=nicrron/auto
PRISMTRACE_API_KEY=         # required sponsor
PRISMTRACE_PROJECT_ID=
PRISMTRACE_HOST=https://api.prism.blockconvey.com
ELEVENLABS_API_KEY=         # optional
```

---

## Auth & onboarding flow (Epic 03)

Demo auth is session-based; no password/OAuth. Guarded pages redirect to `/signin`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | public landing |
| GET/POST | `/signin` | demo email sign-in; sets `session["user"]` |
| GET | `/signout` | clears session |
| GET | `/onboarding` | routes to current phase |
| GET/POST | `/onboarding/connect` | consent + start phase 1 |
| GET | `/onboarding/profile-loading` | spinner shell (calls profile API) |
| GET/POST | `/onboarding/profile` | editable profile; required fields gate |
| GET | `/onboarding/searching` | spinner shell (calls benefits API) |
| GET | `/onboarding/benefits` | benefit cards |
| GET | `/onboarding/benefits/<id>` | form preview + approval |
| POST | `/onboarding/benefits/<id>/submit` | mock submit; creates/updates application |
| GET | `/onboarding/progress/<app_id>` | progress card |
| GET | `/api/onboarding/profile` | `{fields, missing_required, stats}` |
| GET | `/api/onboarding/benefits` | `{benefits}`; marks phase 2 ready |
| POST | `/api/onboarding/benefits/<id>/fill` | `{benefit, fields}` |
| POST | `/api/onboarding/benefits/<id>/submit` | `{approved:true}` required |

**State:** `store.onboarding` — `gmail_connected`, `profile_saved`, `benefits_ready`, `selected_benefit`, `application_id`, `fields`. Reset with `/api/demo/reset`.

**Rules:** required fields (legal name, EIN, address, owner, phone, authorized signer) block Continue; missing fields are coral; approval checkbox is required before submit; submit is mock-only.
