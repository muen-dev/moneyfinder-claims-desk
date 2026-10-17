# Epic 03 — Landing, Demo Auth & the 3-Phase Agent Onboarding

**MONEY TALKS 2 · Money Operations · October 17, 2026**
**Repo:** https://github.com/muen-dev/moneyfinder-claims-desk · **Scope:** front-end flow + thin server state
**Design:** [DESIGN.md](../DESIGN.md) · **Builds on:** the working Claims Desk scaffold (fixtures, claims pipeline, ledger, PRISM emitter)

> **Goal:** a first-time small-business owner can go from a landing page to a signed-in, profile-complete, benefit-selected, form-submitted state in one guided path — with the agent doing the work at every step and the human approving the money-moving moments.

---

## 1. The user

**Marisol**, founder of Gowanus Kettle Brewing Co. LLC (synthetic). She has heard there is government money for small businesses, but she does not know what she qualifies for, does not want to hand over her inbox blindly, and will not send a government form she cannot see and approve.

**Job to be done:** *“Show me what I qualify for, fill the forms from my own data, let me approve, and tell me what happens next.”*

## 2. Flow (the spine)

```
/ (landing)
  └─ CTA “Find my benefits” → /signin
       └─ demo sign-in (email only; no real password)
            └─ /onboarding
                 ├─ PHASE 1 — Gmail consent + crawl
                 │    consent screen (scope, synthetic data, revoke)
                 │    → authorize → **Gmail crawl** screen:
                 │      messages read, facts, conflicts, purchases
                 │    → profile review: every field editable,
                 │      missing fields are coral but **do not block** (time-boxed demo)
                 │    → verification: NYS SLA license, NYS DOS standing,
                 │      NYC zoning/BBL, tax classification, pre-screened incentives
                 │    → continue to benefit search
                 │
                 ├─ PHASE 2 — Benefit search
                 │    → spinner: agent searches public programs
                 │    → benefit cards: name, description, why it fits,
                 │      estimated amount, fit score, source
                 │    → user selects a card
                 │
                 └─ PHASE 3 — Form fill & submit
                      → **form fill screen**: fetch official PDF,
                        read AcroForm fields, fill from profile,
                        verify the saved PDF
                      → form review: every field with source/confidence
                      → user reviews + approves (checkbox)
                      → “Send” → progress card (submitted → agency review)
                      → CTA “Go to dashboard” (application now in the pipeline)
```

## 3. Screens and states

| # | Screen | Must show | States |
|---|---|---|---|
| 1 | **Landing** | value prop, how it works (3 steps), trust/synthetic notice, CTA | default |
| 2 | **Sign in** | demo email field, continue, “no password — synthetic demo” | default, error |
| 3 | **Gmail consent** | read-only scope, what is read/never written, synthetic mailbox, revoke note | default, previously authorized |
| 4 | **Profile loading** | spinner + agent step log (scan, facts, conflicts, purchases) | loading, error |
| 5 | **Profile review** | editable fields, source + confidence per field, required-field markers, coral missing fields | default, validation error |
| 6 | **Benefit search loading** | spinner + “searching official agency pages” log | loading, empty, error |
| 7 | **Benefit cards** | name, agency, description, “why this fits you”, estimated amount, fit score, source link, select | cards, empty |
| 8 | **Benefit detail / form** | official form name + preview, filled fields with source/confidence, missing flags, approval checkbox, Send | default, validation error, submitting |
| 9 | **Progress card** | submitted timestamp, confirmation id, steps (form fetched → filled → approved → sent → processing), next check, dashboard CTA | submitted, processing |
| 10 | **Dashboard** | new application visible in In process; totals update | existing |

**Global:** persistent synthetic banner; keyboard-focusable controls; mobile at 390px; no dead buttons.

## 4. Rules

- **No real Gmail.** The consent screen is a demo affordance; the scan reads `fixtures/inbox.jsonl` (25 synthetic messages). Copy says “synthetic mailbox”.
- **No real filing.** “Send” writes a mock submission event; no agency is contacted. Copy says “mock submission”.
- **No invented eligibility.** Cards come from the curated fixture with source excerpts; fit score is a demo heuristic, labeled as such.
- **Human approval is required** before “Send”.
- **Required fields block progress.** Missing required fields are coral; the Continue button stays disabled until filled.
- **Every filled form field shows its source** (profile fact / email / user edit) and a confidence chip.
- **Demo auth only.** Email sign-in sets a session; no password, no OAuth, no real account. Guarded pages redirect to `/signin`.

## 5. Data & API

New/changed endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | landing (public) |
| GET/POST | `/signin` | demo auth; sets session user |
| GET | `/signout` | clears session |
| GET | `/onboarding` | routes to the current phase |
| POST | `/onboarding/connect` | records Gmail consent; starts phase 1 |
| GET | `/onboarding/profile-loading` | spinner shell |
| GET/POST | `/onboarding/profile` | review/edit/save profile |
| GET | `/onboarding/searching` | spinner shell |
| GET | `/onboarding/benefits` | cards |
| GET | `/onboarding/benefits/<id>` | form preview + approval |
| POST | `/onboarding/benefits/<id>/submit` | mock submit; creates/updates application |
| GET | `/onboarding/progress/<app_id>` | progress card |
| GET | `/api/onboarding/profile` | JSON profile fields |
| GET | `/api/onboarding/benefits` | JSON benefit cards |
| POST | `/api/onboarding/benefits/<id>/fill` | JSON filled form fields |
| POST | `/api/onboarding/benefits/<id>/submit` | JSON submit result |

Fixtures: `fixtures/onboarding.json` — profile fields (required/optional, value, source, confidence) and benefit cards (description, why_fit, fit_score, amount, form fields, progress steps).

State: server-side `store.onboarding` per demo user (`gmail_connected`, `profile_saved`, `benefits_ready`, `selected_benefit`, `application_id`); reset with the demo reset.

PRISM: onboarding emits the same one-session-per-flow trace pattern:
`gmail_permission → gmail_scan → profile_build → profile_review → benefit_search → benefit_match → pdf_fetch → form_fill → user_approval → submit → status_check`.

## 6. Acceptance

- [ ] Landing is public; all app pages redirect to `/signin` when signed out.
- [ ] Sign-in works with the demo email and routes to `/onboarding` (first time) or `/dashboard`.
- [ ] Consent screen explains scope; authorize starts the loading state; profile appears after.
- [ ] Profile fields are editable; saving persists; missing required fields are coral and block Continue.
- [ ] Benefit search shows ≥4 cards with name, description, why-fit, amount, fit score, source.
- [ ] Selecting a card opens the form; fields show source/confidence; missing fields flagged.
- [ ] Send is blocked until approval; submit creates a `SUBMITTED` application with a progress card.
- [ ] Dashboard shows the new application in In process; totals update.
- [ ] Demo reset returns the flow to phase 1.
- [ ] Tests: landing, auth guard, consent, profile validation, benefits, submit, progress, dashboard.
- [ ] PRISM traces emitted for the onboarding flow when configured; pending otherwise.

## 7. Demo script (60 seconds of the 3-minute pitch)

1. Landing → “Find my benefits” → demo sign-in (5s).
2. Consent: “Read-only, synthetic mailbox; I can revoke.” Authorize.
3. Spinner: “It is reading payroll, hires, capex.” Profile appears; phone + authorized rep are coral; fill them; Continue.
4. Spinner: “Searching tax.ny.gov, IRS, NYSERDA.” Cards appear; open IT-643; “Here is why: two veterans hired in 2025.”
5. Form: “Every field has a source; the one empty field is your signature.” Approve → Send.
6. Progress: “Submitted — agency review; confirmation NY-DEMO….” → Dashboard with the application in process.

## 8. Out of scope / P1

- Real Google OAuth, real Gmail, real agency fetch/submit.
- Multi-business accounts, invite flow, password reset.
- Server-side PDF rendering (a styled HTML preview is enough for the demo).
- Live model calls in onboarding (deterministic fixture + optional Nicrron synthesis).
- Email notifications.

## 9. Estimate

**8 points** · O=6h, M=9h, P=14h → `E≈9.8h`, σ≈1.3h. Factor 1.2 h/pt (new UI surfaces, reusable scaffold).
Cut line: landing/auth → consent → profile → cards → form → progress. Never cut: required-field gate, approval checkbox, progress card, dashboard reflection.

## 10. Tasks

- [ ] Landing + public nav + CTA
- [ ] Demo auth (`/signin`, session, guard, signout)
- [ ] Onboarding state in `store` + `fixtures/onboarding.json`
- [ ] Phase 1: consent → loading → editable profile → required-field validation
- [ ] Phase 2: search loading → benefit cards
- [ ] Phase 3: form preview + filled fields + approval + submit
- [ ] Progress card + dashboard reflection
- [ ] PRISM onboarding traces
- [ ] Tests + screenshots + README update
