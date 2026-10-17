# PRD — MoneyFinder Claims Desk (Thuy's PRD)

**Version 1.0 · October 17, 2026 · MONEY TALKS 2 · Track: Money Operations**

## 1. Vision

A small-business owner is owed money by the government — tax credits and rebates they qualify for but never claim because the paperwork is long, the rules are scattered, and nobody tracks what happens after a form is sent.

MoneyFinder is the **agent back office** for that money:
1. learn the business from its own inbox,
2. find and cite the public programs it may qualify for,
3. prepare the applications with provenance and human approval,
4. track every application like a receivable until a deposit is matched,
5. turn the same inbox into a reconciled ledger and accountant packet.

It is a review and paperwork assistant — not the accountant, not the tax filer, not the eligibility authority.

**Persona:** Marisol Vance, Managing Member, Gowanus Kettle Brewing Co. LLC (synthetic) — 14 employees, Brooklyn microbrewery, 2025 tax year on extension, four credits worth $45,737 identified, receipts spread across email.

## 2. Goals

- **G1** Turn a synthetic inbox into a sourced business profile (facts, quotes, conflicts).
- **G2** Find public-agency programs with eligibility reasons and citations; flag expired ones.
- **G3** Track applications across **Found / In process / Approved / Paid** with honest money semantics.
- **G4** Build a claim-ready 2025 ledger and accountant packet from the same inbox.
- **G5** Run real reasoning through **Nicrron** and observable execution in **PRISM**.

**Non-goals:** real filings, legal/tax conclusions, live financial transfers, guaranteed savings, real Gmail access, autonomous external actions.

## 3. Users and job

| User | Job |
|---|---|
| Owner (Marisol) | “Tell me what I qualify for, file the paperwork, and tell me when the check clears — and give my accountant clean books.” |
| Accountant (Owen Halloran CPA) | “Give me a ledger and evidence index I can review, not a shoebox of forwarded emails.” |
| Judge | “Show a real agent doing real work with PRISM proofs and Nicrron calls.” |

## 4. Screens

1. **Onboarding** — connect synthetic Gmail → scan → facts with source quotes → conflicts (coral) → consent.
2. **Claims Desk** — four columns, totals, next action per card, recent runs, integration status.
3. **Application detail** — amount, evidence, official form, allowed status transitions, event log.
4. **Eligibility** — program cards with verdict, reasons, questions, source excerpt, `as_of`.
5. **Books** — ledger summary, exceptions (missing receipts, duplicates), 39-row table, packet build/download.
6. **Run History** — 12 steps, local vs PRISM, telemetry status, failed-run root cause.
7. **Settings** — modes, integrations, reset demo.

## 5. Functional requirements

- **FR-1 Sourced profile:** every fact has `source_message_id`/`source_kind`, quote, confidence; facts without a source are discarded.
- **FR-2 Conflicts:** contradictory values are preserved and surfaced; never silently resolved.
- **FR-3 Eligibility:** every verdict cites an official URL + excerpt + `as_of`; expired programs cannot open an application; unknown fields become one question.
- **FR-4 Status machine:** only allowed transitions; `PAYMENT_ISSUED` ≠ `PAYMENT_CONFIRMED`; deposit confirmation requires a matched mock deposit.
- **FR-5 Money semantics:** identified = estimate; in process = filed/awaiting docs; approved = agency evidence; paid = matched deposit. Never conflate.
- **FR-6 Ledger:** integer cents; duplicates excluded from totals but surfaced; missing receipts flagged; reconciled delta shown.
- **FR-7 Packet:** Markdown + CSV + XLSX; evidence index, open questions, limitations; “prepared for review, not filed.”
- **FR-8 Run:** 12 steps, one PRISM session, failed tool blocks a complete finding, telemetry reported honestly.
- **FR-9 Nicrron:** OpenAI-compatible, server-side only, explicit failure; no silent fake success.
- **FR-10 Safety:** synthetic data only; no email send, Gmail write, filing, transaction modification or third-party submission.
- **FR-11 Reset:** one action restores fixtures; never touches external systems.
- **FR-12 API:** every screen has a JSON contract; teammates can build parallel UIs.

## 6. Acceptance

- All four columns render from fixtures; totals are $45,737 / $15,075 / $7,460 / $0.
- Onboarding shows 14 facts, 3 conflicts, 25 messages, 39 purchases.
- Eligibility shows 4 eligible, 1 needs_info, 1 expired, 1 not_eligible, each with a citation.
- Ledger: 39 transactions, 3 missing receipts, 1 duplicate, capital $228,000, delta $0.
- Packet downloads; files open; packet totals match the Books page.
- Illegal transition rejected; deposit confirmation rejected before `PAYMENT_ISSUED`.
- Run has 12 steps; `human_approve` is pending; telemetry `pending` without PRISM, `ok` after live traces.
- `make test` green (12 tests).

## 7. Track fit

Money Operations: receivables tracking, exception queue, expense/ledger reconciliation, professional handoff, CFO-facing next actions. PRISM proofs: 12-step session, alert on failed tool/partial run, 3+ failed-run root cause and v2 fix. Nicrron: model calls through one OpenAI-compatible key.

## 8. Out of scope / P1–P2

- **P1:** live Gmail read-only for the synthetic mailbox, live official-page fetch (replace cached excerpts), ElevenLabs spoken summary, CSV import UI.
- **P2:** real program rules behind release review, multi-business, reminders, production access control.
