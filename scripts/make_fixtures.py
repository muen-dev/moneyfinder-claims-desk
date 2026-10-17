"""Generate the demo fixtures from the synthetic Gowanus Kettle dataset.

Run:  .venv/bin/python scripts/make_fixtures.py
Everything here is synthetic; no real business, person, or filing is described.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"


def inbox() -> dict[str, dict]:
    return {m["id"]: m for m in (json.loads(line) for line in (FIX / "inbox.jsonl").read_text().splitlines())}


def main() -> None:
    msgs = inbox()
    business = json.loads((FIX / "business.json").read_text())

    def quote(mid: str, text: str) -> str:
        return text

    facts = [
        {"key": "legal_name", "label": "Legal name", "value": "Gowanus Kettle Brewing Co. LLC",
         "source_message_id": "synthetic-gk-001", "source_kind": "email", "confidence": 0.99,
         "quote": "Payroll processed for Gowanus Kettle Brewing Co. LLC"},
        {"key": "entity_type", "label": "Entity type", "value": "Domestic LLC (NY)",
         "source_kind": "registry", "confidence": 0.97, "quote": "NY Department of State record"},
        {"key": "naics", "label": "NAICS", "value": "312120 — Breweries",
         "source_kind": "web", "confidence": 0.92, "quote": "Craft beer brewed on a 15-barrel brewhouse"},
        {"key": "headcount", "label": "Employees at year end", "value": "14",
         "source_message_id": "synthetic-gk-022", "source_kind": "email", "confidence": 0.95,
         "quote": "We ended 2025 with 14 employees."},
        {"key": "payroll_provider", "label": "Payroll provider", "value": "Gusto",
         "source_message_id": "synthetic-gk-004", "source_kind": "email", "confidence": 0.99,
         "quote": "14 employees paid. Total gross pay: $48,960.00."},
        {"key": "address", "label": "HQ address", "value": "417 Sackett Street, Brooklyn, NY 11231",
         "source_message_id": "synthetic-gk-012", "source_kind": "email", "confidence": 0.98,
         "quote": "417 Sackett Street, Brooklyn, NY 11231"},
        {"key": "ein", "label": "EIN", "value": "00-4271985",
         "source_kind": "registry", "confidence": 0.99, "quote": "Synthetic EIN (00- prefix is never issued)"},
        {"key": "veterans_hired", "label": "Veteran hires (2025)", "value": "2",
         "source_message_id": "synthetic-gk-009", "source_kind": "email", "confidence": 0.94,
         "quote": "Darnell dropped off his DD-214 … Keisha (Marine Corps) should start in August"},
        {"key": "canning_line", "label": "Canning line (placed in service)", "value": "$186,500 · July 28, 2025",
         "source_message_id": "synthetic-gk-022", "source_kind": "email", "confidence": 0.98,
         "quote": "canning line invoice ($186,500, placed in service July 28, 2025)"},
        {"key": "tips", "label": "Taproom tips (2025)", "value": "$148,600",
         "source_message_id": "synthetic-gk-025", "source_kind": "email", "confidence": 0.85,
         "quote": "Tips collected for bartenders: $2,906 (weekly summary)"},
        {"key": "barrels", "label": "NY barrels brewed (2025)", "value": "3,104",
         "source_message_id": "synthetic-gk-012", "source_kind": "email", "confidence": 0.98,
         "quote": "2025 calendar-year production reported in New York: 3,104 barrels of beer."},
        {"key": "tax_year", "label": "Tax year", "value": "2025",
         "source_message_id": "synthetic-gk-005", "source_kind": "email", "confidence": 0.99,
         "quote": "Your W-2s and Form 941 filings for tax year 2025 are complete"},
        {"key": "health_plan", "label": "Small-group health plan", "value": "Oscar via NY State of Health SHOP",
         "source_message_id": "synthetic-gk-019", "source_kind": "email", "confidence": 0.96,
         "quote": "Purchased through: NY State of Health small business marketplace (SHOP)"},
        {"key": "accountant", "label": "Accountant", "value": "Owen Halloran CPA",
         "source_message_id": "synthetic-gk-021", "source_kind": "email", "confidence": 0.97,
         "quote": "Owen Halloran CPA — 2025 tax year documents"},
    ]

    conflicts = [
        {"field": "headcount", "label": "Headcount: 14 vs 12",
         "profile_value": "14 (year end)", "email_value": "12 (March payroll)",
         "source_message_id": "synthetic-gk-001",
         "note": "March payroll lists 12 employees paid; December payroll and the owner email say 14.",
         "status": "open", "options": ["Use 14 (year end)", "Use 12 (March)", "Ask me"]},
        {"field": "legal_name", "label": "Legal name variant",
         "profile_value": "Gowanus Kettle Brewing Co. LLC", "email_value": "Gowanus Kettle Brewing Co.",
         "source_message_id": "synthetic-gk-014",
         "note": "Some vendor emails omit the 'LLC'. The registry/legal name wins for forms.",
         "status": "open", "options": ["Use the LLC name", "Use the short name"]},
        {"field": "attachment", "label": "DD-214 attachment missing",
         "profile_value": "2 veteran hires", "email_value": "DD-214 'attached' but no file record",
         "source_message_id": "synthetic-gk-022",
         "note": "The email says the DD-214s are attached; the mailbox has no attachment record. Collect them before filing.",
         "status": "open", "options": ["Request the DD-214s", "Defer"]},
    ]

    messages = []
    for mid, m in msgs.items():
        row = {
            "id": mid, "sender": m["sender"], "date": m["date"], "subject": m["subject"],
            "snippet": m.get("snippet", ""), "body": m.get("body", ""),
            "attachments": m.get("attachments", []),
            "attachment_state": "available" if m.get("attachments") else "none",
        }
        if mid == "synthetic-gk-022":
            row["attachment_state"] = "claimed"
        if mid == "synthetic-gk-009":
            row["attachment_state"] = "claimed"
        messages.append(row)

    profile = {
        "business_id": "demo-gowanuskettle",
        "generated_at": "2026-10-17T12:00:00+00:00",
        "demo": True,
        "facts": facts,
        "conflicts": conflicts,
        "messages": messages,
    }
    (FIX / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")

    def app(id_, program_id, program, form, agency, amount, status, next_action, evidence, url):
        return {"id": id_, "program_id": program_id, "program": program, "form": form, "agency": agency,
                "amount_estimate_cents": amount, "amount_type": "estimate", "status": status,
                "next_action": next_action, "deadline": "2026-04-15", "expected_by": None,
                "confidence": 0.9, "source_url": url, "evidence": evidence}

    applications = [
        app("app_it636", "nys_beer_production", "Alcoholic Beverage Production Credit", "IT-636",
            "NYS Department of Taxation and Finance", 1347100, "MATCH_FOUND",
            "Confirm the 3,104-barrel count, then prepare IT-636",
            [{"kind": "email", "ref": "synthetic-gk-012", "excerpt": "3,104 barrels of beer brewed in NY"}],
            "https://www.tax.ny.gov/pdf/current_forms/it/it636_fill_in.pdf"),
        app("app_8846", "fed_fica_tip", "FICA tip credit", "8846", "IRS", 973100, "FORM_READY",
            "Confirm the tips total and approve Form 8846",
            [{"kind": "email", "ref": "synthetic-gk-025", "excerpt": "Tips collected for bartenders"}],
            "https://www.irs.gov/forms-pubs/about-form-8846"),
        app("app_it643", "nys_hire_a_veteran", "Hire a Veteran Credit", "IT-643",
            "NYS Department of Taxation and Finance", 1507500, "SUBMITTED",
            "Upload the DD-214s and sign IT-643",
            [{"kind": "email", "ref": "synthetic-gk-009", "excerpt": "Darnell dropped off his DD-214"}],
            "https://www.tax.ny.gov/pdf/current_forms/it/it643_fill_in.pdf"),
        app("app_it212", "nys_investment", "Investment Credit", "IT-212",
            "NYS Department of Taxation and Finance", 746000, "APPROVED",
            "Agency said yes — wait for the deposit and match it",
            [{"kind": "email", "ref": "synthetic-gk-015", "excerpt": "Amount: $186,500.00"}],
            "https://www.tax.ny.gov/pdf/current_forms/it/it212_fill_in.pdf"),
    ]
    (FIX / "applications.json").write_text(json.dumps(applications, indent=2) + "\n")

    def program(id_, name, form, agency, url, verdict, reasons, questions, excerpt, status="active", confidence=0.9):
        return {"id": id_, "name": name, "form": form, "agency": agency, "jurisdiction": "NY" if "NY" in agency else "federal",
                "url": url, "verdict": verdict, "reasons": reasons, "questions": questions,
                "source_excerpt": excerpt, "as_of": "2026-10-17", "status": status, "confidence": confidence}

    programs = [
        program("nys_beer_production", "Alcoholic Beverage Production Credit", "IT-636", "NYS DTF",
                "https://www.tax.ny.gov/pdf/current_forms/it/it636_fill_in.pdf", "eligible",
                ["NY brewery", "3,104 barrels brewed in NY in 2025"], [],
                "Credit for beer produced in New York; 14 cents per gallon.", confidence=0.93),
        program("nys_investment", "Investment Credit", "IT-212", "NYS DTF",
                "https://www.tax.ny.gov/pdf/current_forms/it/it212_fill_in.pdf", "eligible",
                ["Canning line placed in service July 2025", "$186,500 qualified investment"], [],
                "Credit for qualified tangible personal property placed in service in NY.", confidence=0.91),
        program("nys_hire_a_veteran", "Hire a Veteran Credit", "IT-643", "NYS DTF",
                "https://www.tax.ny.gov/pdf/current_forms/it/it643_fill_in.pdf", "eligible",
                ["Two veterans hired in 2025", "NY employer"], [],
                "Credit for hiring a qualified veteran; 15% of first-year wages.", confidence=0.9),
        program("fed_fica_tip", "FICA tip credit", "8846", "IRS",
                "https://www.irs.gov/forms-pubs/about-form-8846", "eligible",
                ["Taproom tips reported in payroll", "$148,600 tips"], [],
                "Credit for employer Social Security and Medicare taxes paid on tips.", confidence=0.88),
        program("fed_wotc", "Work Opportunity Tax Credit", "", "IRS",
                "https://www.irs.gov/businesses/small-businesses-self-employed/work-opportunity-tax-credit",
                "expired", ["Program lapsed for hires who start after 2025-12-31"], [],
                "Lapsed for employees who start work after 2025-12-31; recheck before filing.", status="expired"),
        program("nyserda_solar", "NYSERDA solar incentive", "", "NYSERDA",
                "https://www.nyserda.ny.gov/All-Programs/Solar", "needs_info",
                ["38 kW rooftop solar installed", "Con Edison interconnection permission received"],
                ["Is the array owner-owned or third-party-owned?"],
                "Incentive depends on ownership and interconnection.", confidence=0.72),
        program("nyc_commercial_rent", "Commercial Rent Tax credit", "", "NYC DOF",
                "https://www.nyc.gov/site/finance/taxes/business-commercial-rent-tax.page", "not_eligible",
                ["Rent below the Commercial Rent Tax threshold", "Not registered for CRT"],
                [], "Applies to Manhattan commercial tenants above the annual rent threshold.", confidence=0.83),
    ]
    (FIX / "programs.json").write_text(json.dumps(programs, indent=2) + "\n")

    # ---- ledger ------------------------------------------------------
    def txn(id_, date, vendor, desc, amount, direction="purchase", category="other",
            source="", quote="", needs_receipt=False, duplicate_of=None, treatment="expense"):
        return {"id": id_, "date": date, "vendor": vendor, "description": desc, "amount_cents": amount,
                "direction": direction, "category": category, "tax_treatment": treatment,
                "payment_account": "Chase for Business ...4410", "source_message_id": source,
                "source_quote": quote, "confidence": 0.95, "needs_receipt": needs_receipt,
                "duplicate_of": duplicate_of, "status": "needs_review" if needs_receipt else "verified"}

    ledger_rows = [
        txn("txn_rev_01", "2025-03-31", "Square (taproom Q1)", "Taproom net sales — Q1", 31240000, "credit", "revenue", "synthetic-gk-025", "Taproom net sales this week", treatment="not_applicable"),
        txn("txn_rev_02", "2025-06-30", "Square (taproom Q2)", "Taproom net sales — Q2", 36890000, "credit", "revenue", "synthetic-gk-025", "Weekly sales summary", treatment="not_applicable"),
        txn("txn_rev_03", "2025-09-30", "Square (taproom Q3)", "Taproom net sales — Q3", 40120000, "credit", "revenue", "synthetic-gk-025", "Weekly sales summary", treatment="not_applicable"),
        txn("txn_rev_04", "2025-12-31", "Square (taproom Q4)", "Taproom net sales — Q4", 37750000, "credit", "revenue", "synthetic-gk-025", "Weekly sales summary", treatment="not_applicable"),
        txn("txn_rev_05", "2025-12-31", "Wholesale accounts", "Wholesale invoices — 2025", 61200000, "credit", "revenue", "synthetic-gk-025", "Weekly sales summary", treatment="not_applicable"),
        txn("txn_rev_06", "2025-12-31", "Events & private parties", "Events revenue — 2025", 6800000, "credit", "revenue", "synthetic-gk-025", "Weekly sales summary", treatment="not_applicable"),
        txn("txn_pay_01", "2025-03-31", "Gusto", "Payroll — Q1", 12575000, "purchase", "payroll", "synthetic-gk-001", "Total gross pay: $41,880.00"),
        txn("txn_pay_02", "2025-06-30", "Gusto", "Payroll — Q2", 12575000, "purchase", "payroll", "synthetic-gk-004", "Total gross pay"),
        txn("txn_pay_03", "2025-09-30", "Gusto", "Payroll — Q3", 12575000, "purchase", "payroll", "synthetic-gk-004", "Total gross pay"),
        txn("txn_pay_04", "2025-12-31", "Gusto", "Payroll — Q4", 12575000, "purchase", "payroll", "synthetic-gk-004", "Year-end: 14 W-2s"),
        txn("txn_pay_tax", "2025-12-31", "Gusto", "Employer payroll taxes", 3800000, "purchase", "payroll_taxes", "synthetic-gk-004", "Employer taxes: $3,977.40"),
        txn("txn_tips", "2025-12-31", "Payroll (taproom tips)", "Tips reported for bartenders — 2025", 14860000, "purchase", "tips", "synthetic-gk-025", "Tips collected for bartenders: $2,906"),
        txn("txn_hops_01", "2025-04-15", "Hop Union", "Hop contracting — spring", 11800000, "purchase", "cogs_ingredients", "", "Spring hop contracting is open", needs_receipt=True),
        txn("txn_hops_02", "2025-09-02", "New York Hop Guild", "Hop pellets — fall", 9400000, "purchase", "cogs_ingredients", "", ""),
        txn("txn_pkg_01", "2025-05-20", "Ball Corp", "Cans and ends — 2025", 6200000, "purchase", "cogs_packaging", "", ""),
        txn("txn_pkg_02", "2025-10-10", "Label Craft", "Labels and cartons", 3400000, "purchase", "cogs_packaging", "", ""),
        txn("txn_rent_01", "2025-03-31", "Sackett Street LLC", "Rent — Q1", 2400000, "purchase", "rent", "", ""),
        txn("txn_rent_02", "2025-06-30", "Sackett Street LLC", "Rent — Q2", 2400000, "purchase", "rent", "", ""),
        txn("txn_rent_03", "2025-09-30", "Sackett Street LLC", "Rent — Q3", 2400000, "purchase", "rent", "", ""),
        txn("txn_rent_04", "2025-12-31", "Sackett Street LLC", "Rent — Q4", 2400000, "purchase", "rent", "", ""),
        txn("txn_util_01", "2025-04-30", "Con Edison", "Electricity + solar net metering", 1280000, "purchase", "utilities", "synthetic-gk-018", "Amount due: $2,114.58"),
        txn("txn_util_02", "2025-08-31", "Con Edison", "Electricity — summer", 1540000, "purchase", "utilities", "synthetic-gk-018", "Amount due: $2,114.58"),
        txn("txn_util_03", "2025-12-31", "Con Edison", "Electricity — winter", 1020000, "purchase", "utilities", "synthetic-gk-018", "Amount due: $2,114.58"),
        txn("txn_ins", "2025-01-06", "Oscar for Business", "Small-group health plan", 1870000, "purchase", "insurance", "synthetic-gk-019", "Enrolled employees: 11"),
        txn("txn_sw_01", "2025-02-01", "Gusto", "Payroll software — annual", 480000, "purchase", "software", "", ""),
        txn("txn_sw_02", "2025-07-01", "Square", "POS subscription — annual", 500000, "purchase", "software", "", ""),
        txn("txn_prof_01", "2025-12-31", "Owen Halloran CPA", "Tax prep — 2025", 840000, "purchase", "professional_fees", "synthetic-gk-021", "2025 tax year documents"),
        txn("txn_prof_02", "2025-10-15", "Harbor Benefits", "Benefits brokerage", 400000, "purchase", "professional_fees", "synthetic-gk-020", "2026 renewal + Form 8941 numbers"),
        txn("txn_mkt", "2025-08-20", "Brooklyn Brewery Alliance", "Sponsorship and ads", 1690000, "purchase", "marketing", "", "", needs_receipt=True),
        txn("txn_rep", "2025-06-12", "Kettle Repair Co.", "Brewhouse repair", 1420000, "purchase", "repairs", "", "", needs_receipt=True),
        txn("txn_lic", "2025-11-03", "NYS Liquor Authority", "License renewal", 830000, "purchase", "licenses", "synthetic-gk-012", "License renewal approved"),
        txn("txn_capex_01", "2025-07-28", "ProBrew Equipment", "Canning line — 24-head filler/seamer", 18650000, "purchase", "capital_assets", "synthetic-gk-015", "Amount: $186,500.00", treatment="capitalized"),
        txn("txn_capex_02", "2025-09-15", "Taproom Build LLC", "Taproom equipment and fixtures", 4150000, "purchase", "capital_assets", "", "", treatment="capitalized"),
        txn("txn_capex_dup", "2025-07-28", "ProBrew Equipment", "Canning line (duplicate entry)", 18650000, "purchase", "capital_assets", "synthetic-gk-015", "Amount: $186,500.00", duplicate_of="txn_capex_01", treatment="capitalized"),
    ]
    for i in range(1, 6):
        ledger_rows.append(txn(f"txn_supp_{i:02d}", f"2025-0{i+2}-14", "Restaurant Depot",
                               "Taproom supplies", 42000 + i * 5000, "purchase", "other", "", ""))
    ledger = {"meta": {"year": 2025, "reconciled_delta_cents": 0, "source": "synthetic inbox + statements"},
              "transactions": ledger_rows}
    (FIX / "ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")

    # ---- runs --------------------------------------------------------
    step_names = ["gmail_scan", "extract_facts", "extract_purchases", "categorize_ledger",
                  "reconcile_ledger", "program_candidates", "agency_fetch", "eligibility_extract",
                  "match_score", "form_prep", "human_approve", "build_accountant_packet"]
    tools = ["scan_inbox", "extract_facts", "extract_purchases", "categorize_ledger", "reconcile_ledger",
             "find_candidates", "fetch_program_page", "extract_eligibility", "score_match",
             "prepare_application", "request_approval", "build_accountant_packet"]

    def steps(failed_at: int | None = None, v2: bool = False):
        out = []
        for i, (name, tool) in enumerate(zip(step_names, tools)):
            if failed_at is not None and i == failed_at:
                out.append({"step": name, "tool": tool, "status": "failed", "latency_ms": 820,
                            "error": "citation missing: eligibility criterion has no verbatim quote",
                            "prism_delivered": False})
            elif failed_at is not None and i > failed_at:
                out.append({"step": name, "tool": tool, "status": "skipped", "latency_ms": 0,
                            "error": None, "prism_delivered": False})
            elif name == "human_approve":
                out.append({"step": name, "tool": tool, "status": "pending", "latency_ms": 0,
                            "error": None, "prism_delivered": True})
            else:
                out.append({"step": name, "tool": tool, "status": "succeeded", "latency_ms": 240 + i * 30,
                            "error": None, "prism_delivered": True})
        return out

    runs = [
        {"id": "run_demo_001", "case_id": "case_gowanus_2025", "version": "v1", "status": "succeeded",
         "started_at": "2026-10-17T12:10:00+00:00", "ended_at": "2026-10-17T12:10:09+00:00",
         "steps": steps(), "telemetry": "pending", "prism_session_id": "run_demo_001", "prism_url": None,
         "error": None, "awaiting_approval": True,
         "summary": {"facts": 14, "transactions": len(ledger_rows), "programs": len(programs), "packet_files": 3}},
        {"id": "run_fail_001", "case_id": "case_eligibility_v1", "version": "v1", "status": "failed",
         "started_at": "2026-10-17T11:40:00+00:00", "ended_at": "2026-10-17T11:40:05+00:00",
         "steps": steps(failed_at=7), "telemetry": "pending", "prism_session_id": "run_fail_001",
         "prism_url": None, "error": "eligibility_extract failed: citation missing"},
        {"id": "run_fail_002", "case_id": "case_eligibility_v1", "version": "v1", "status": "failed",
         "started_at": "2026-10-17T11:41:00+00:00", "ended_at": "2026-10-17T11:41:05+00:00",
         "steps": steps(failed_at=7), "telemetry": "pending", "prism_session_id": "run_fail_002",
         "prism_url": None, "error": "eligibility_extract failed: citation missing"},
        {"id": "run_fail_003", "case_id": "case_eligibility_v1", "version": "v1", "status": "failed",
         "started_at": "2026-10-17T11:42:00+00:00", "ended_at": "2026-10-17T11:42:05+00:00",
         "steps": steps(failed_at=7), "telemetry": "pending", "prism_session_id": "run_fail_003",
         "prism_url": None, "error": "eligibility_extract failed: citation missing"},
        {"id": "run_v2_001", "case_id": "case_eligibility_v2", "version": "v2", "status": "succeeded",
         "started_at": "2026-10-17T11:50:00+00:00", "ended_at": "2026-10-17T11:50:08+00:00",
         "steps": steps(v2=True), "telemetry": "pending", "prism_session_id": "run_v2_001",
         "prism_url": None, "error": None},
    ]
    (FIX / "runs.json").write_text(json.dumps(runs, indent=2) + "\n")

    print(f"fixtures written: {len(facts)} facts, {len(applications)} applications, "
          f"{len(programs)} programs, {len(ledger_rows)} transactions, {len(runs)} runs")


if __name__ == "__main__":
    main()
