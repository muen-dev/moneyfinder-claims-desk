# Team Plan — 3 People, Parallel

**Repo:** this one · **Freeze:** 16:15 · **Demo:** 2-min video + 3-min pitch
**PRD:** `docs/PRD.md` · **Epic:** `docs/EPIC.md` · **Contract:** `docs/CONTRACT.md`

| Person | Role | Owns | Branch |
|---|---|---|---|
| **Thuy** | Product Designer · PRISM owner | Onboarding, Dashboard, Eligibility, Books UI; design tokens; copy/QA; PRISM proofs; repo | `feat/thuy-onboarding-prism` |
| **Kenan** | Developer · Demo owner | Application detail, Run History, Settings, UI shell; 2-min video; live pitch; submission | `feat/kenan-desk-books` |
| **Richard** | Developer · platform/agent | API, store, orchestrator, ledger/packet, Nicrron/PRISM, tests, fixtures | `feat/richard-ledger-agent` |

## Shared core first

The scaffold is functional against fixtures. Until the contract changes:
- UI reads fixtures / API, never blocks on a missing backend piece.
- Richard keeps `app/routes/api.py` and `app/services/**` stable; announce shape changes.
- No one edits another owner's files without a one-line request.

## Timeline

| Clock | Thuy | Kenan | Richard |
|---|---|---|---|
| 12:55–13:15 | PRISM proofs setup; copy review | UI shell + demo route check | API/run verification; fixture polish |
| 13:15–14:15 | Onboarding + Dashboard polish | Application detail + Run History + Settings | Live eligibility fetch (cached fallback), packet XLSX |
| 14:15–14:30 | **CP1** merge + demo path | **CP1** | **CP1** |
| 14:30–15:35 | Eligibility + Books polish; proof screenshots | Transactions/Books interaction; demo script | CSV import (P1), PRISM 50-run seed, v1/v2 |
| 15:35–15:50 | **CP2** end-to-end | **CP2** | **CP2** |
| 15:50–16:15 | PRISM proofs final; video claims review | Record 2-min video | Root-cause screenshots; README |
| 16:15 | **FREEZE** (`git tag demo-freeze`) | — | — |
| 16:15–17:00 | Submission visuals | Upload + submit | Repo/README check |
| 17:00–18:00 | Pitch PRISM segment | Rehearse | Buffer |

## Demo path

`/dashboard` → `/onboarding` (scan + conflicts) → `/eligibility` (expired WOTC) → `/applications/app_it643` (transition) → `/books` (packet) → `/run-history` (12 steps, telemetry) → `/settings` (integrations).

## PRISM proofs (Thuy)

- [ ] project + credential verified; 12 live traces delivered
- [ ] 50+ runs seeded
- [ ] one run, 12 steps (≥7 local, ≥6 verified)
- [ ] alert rule firing on failed tool / partial run
- [ ] failed-run cluster (3+) with cause; v2 passes the same inputs
- [ ] screenshots in `docs/proofs/`; Run History shows verified link only

## Scope cut

- **Must:** dashboard, onboarding, eligibility, application transitions, books + packet, run history (12 steps), Nicrron/PRISM, tests, video.
- **P1:** live official-page fetch, CSV import UI, ElevenLabs summary, XLSX polish.
- **Never cut:** money semantics, expired-program handling, packet download, PRISM 12-step proof, persistent synthetic banner.

## Rules

- `.env` never committed; `.env.example` names only.
- Synthetic data only; `.example` domains.
- Rebase before push; PR with one reviewer; `main` is demo.
- Every claim has a source or an explicit missing status.
