"""Application status machine and pipeline aggregation (money semantics live here)."""
from __future__ import annotations

STATUSES = [
    "MATCH_FOUND", "FORM_READY", "USER_APPROVED", "SUBMITTED", "CLAIM_RECEIVED",
    "PROCESSING", "NEEDS_DOCS", "APPROVED", "PAYMENT_ISSUED", "PAYMENT_CONFIRMED",
    "REJECTED", "STOPPED_BY_USER",
]

COLUMNS = {
    "MATCH_FOUND": "found", "FORM_READY": "found",
    "USER_APPROVED": "in_process", "SUBMITTED": "in_process", "CLAIM_RECEIVED": "in_process",
    "PROCESSING": "in_process", "NEEDS_DOCS": "in_process",
    "APPROVED": "approved",
    "PAYMENT_ISSUED": "paid", "PAYMENT_CONFIRMED": "paid",
    "REJECTED": "closed", "STOPPED_BY_USER": "closed",
}

ALLOWED = {
    "MATCH_FOUND": {"FORM_READY", "STOPPED_BY_USER"},
    "FORM_READY": {"USER_APPROVED", "MATCH_FOUND", "STOPPED_BY_USER"},
    "USER_APPROVED": {"SUBMITTED", "FORM_READY", "STOPPED_BY_USER"},
    "SUBMITTED": {"CLAIM_RECEIVED", "STOPPED_BY_USER"},
    "CLAIM_RECEIVED": {"PROCESSING", "NEEDS_DOCS", "REJECTED"},
    "PROCESSING": {"APPROVED", "NEEDS_DOCS", "REJECTED", "PROCESSING"},
    "NEEDS_DOCS": {"PROCESSING", "FORM_READY", "STOPPED_BY_USER"},
    "APPROVED": {"PAYMENT_ISSUED", "PROCESSING"},
    "PAYMENT_ISSUED": {"PAYMENT_CONFIRMED"},
    "PAYMENT_CONFIRMED": set(),
    "REJECTED": set(),
    "STOPPED_BY_USER": set(),
}


def transition_allowed(frm: str, to: str) -> bool:
    return to in ALLOWED.get(frm, set())


def pipeline(applications: list[dict]) -> dict:
    columns = {"found": [], "in_process": [], "approved": [], "paid": [], "closed": []}
    totals = {
        "identified_cents": 0,
        "in_process_cents": 0,
        "approved_cents": 0,
        "paid_issued_cents": 0,
        "paid_confirmed_cents": 0,
    }
    for app in applications:
        col = COLUMNS.get(app.get("status"), "closed")
        app["column"] = col
        columns[col].append(app)
        amount = int(app.get("amount_estimate_cents") or 0)
        totals["identified_cents"] += amount
        if col == "in_process":
            totals["in_process_cents"] += amount
        elif col == "approved":
            totals["approved_cents"] += amount
        elif col == "paid":
            if app.get("status") == "PAYMENT_CONFIRMED":
                totals["paid_confirmed_cents"] += amount
            else:
                totals["paid_issued_cents"] += amount
    totals["paid_cents"] = totals["paid_confirmed_cents"]
    return {"columns": columns, "totals": totals, "count": len(applications)}
