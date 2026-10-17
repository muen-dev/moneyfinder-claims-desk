# Reuse map — `thetradingdoc/moneyfinder` → `moneyfinder-claims-desk`

Source: https://github.com/thetradingdoc/moneyfinder (read-only reference; not modified).

## Gmail scrape

- `research/business/src/business_research/gmail/auth.py` — Google web-server OAuth, scope `gmail.readonly`, one token per business, refresh + revoke.
- `gmail/client.py` — `search_ids` / `search` (Gmail query syntax, pagination, retries), `get` (format=full).
- `gmail/parse.py` — flattens headers/body/attachment names into `EmailMessage`.
- `business_research/email_facts.py` — deterministic sender/amount/EIN/headcount rules, then LLM facts grounded by quote.
- `live_demo.py` — end-to-end: synthetic Gmail mailbox → facts → dossier → forms.

**Port status:** not ported; claims-desk onboarding uses the synthetic inbox + deterministic profile fixture. Porting needs Google OAuth client credentials and two callback routes (`/oauth/start`, `/oauth/callback`).

## Benefits search

- `research/legal/` — catalog (`programs.toml`, `niches.toml`, `sources.toml`), official-page crawl, form PDF links, `run --search` via Tavily/Nimble, official-host allowlist.
- `legal_research/match.py` — NAICS/keyword matching of a company profile to programs.

**Port status:** claims-desk uses `fixtures/onboarding.json` benefits with cached official-page excerpts. A later port can replace the fixture with `legal-research` output.

## Form fill

- `form-filling/demo_forms.py` — downloads the *official* IT-636/IT-212/IT-643/8846 PDFs, fills AcroForm fields with pypdf, writes `filled/*.pdf` + manifest.
- `form-filling/fill_pdf.py` — Anchor Browser + PDF.js fills IT-636 live and reads values back (no submit).
- `form-filling/fill.py` — fills the mock portal from a dossier; DOM read-back diff; never submits.

**Port status:** the pypdf fill is **ported** into `app/services/pdf_fill.py`:
- blank official PDFs cached in `fixtures/forms/`
- values derived from onboarding profile + demo business
- route `GET /onboarding/benefits/<benefit_id>/pdf` returns the filled PDF
- test `test_filled_official_pdf_downloads` asserts a real `%PDF` download.

## Demo business

`demo/gowanus-kettle/` (business, 25-message inbox, dossier profile, filled forms) is reused as claims-desk's fixture source. All synthetic; `.example` domains, `00-` EIN.


## Verification engine (Kenan)

Kenan's AI Studio app `Moneyfinder Verification Engine` provides the craft-beverage
screener: NYS SLA license status, NYS DOS standing, NYC zoning/BBL and federal tax
classification, then deterministic incentive pre-screens (IT-636, FICA tip, REAP).

Ported as a synthetic first version:
- `fixtures/verification.json` — registry snapshot (SLA 1314509, DOS 5201948, BBL 3004620014, M1-1 IBZ)
- `app/services/verification.py` — resolves profile inputs + checks + incentives
- `app/templates/verification.html` — explicit stage after profile review
- `POST /api/onboarding/verify` — runs checks, emits `verify_*` PRISM spans

Live SODA/Open Data calls are not wired in this demo; the snapshot is labeled synthetic.
