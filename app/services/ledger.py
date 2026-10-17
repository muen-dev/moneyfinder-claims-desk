"""Ledger aggregation and reconciliation. All money math is code, in integer cents."""
from __future__ import annotations

from collections import defaultdict


def transactions(ledger: dict) -> list[dict]:
    return list(ledger.get("transactions", []))


def summary(ledger: dict) -> dict:
    all_rows = transactions(ledger)
    rows = [r for r in all_rows if not r.get("duplicate_of")]
    revenue = sum(r["amount_cents"] for r in rows if r.get("direction") == "credit")
    capital = sum(r["amount_cents"] for r in rows if r.get("category") == "capital_assets")
    expenses = sum(r["amount_cents"] for r in rows
                   if r.get("direction") == "purchase" and r.get("category") != "capital_assets")
    payroll = sum(r["amount_cents"] for r in rows if r.get("category") in {"payroll", "payroll_taxes"})
    tips = sum(r["amount_cents"] for r in rows if r.get("category") == "tips")
    missing = [r for r in rows if r.get("needs_receipt")]
    duplicates = [r for r in rows if r.get("duplicate_of")]
    by_category = defaultdict(int)
    for r in rows:
        by_category[r.get("category", "other")] += r["amount_cents"]
    meta = ledger.get("meta", {})
    return {
        "year": meta.get("year", 2025),
        "revenue_cents": revenue,
        "expense_cents": expenses,
        "capital_cents": capital,
        "payroll_cents": payroll,
        "tips_cents": tips,
        "net_cents": revenue - expenses,
        "reconciled_delta_cents": int(meta.get("reconciled_delta_cents", 0)),
        "missing_receipts": len(missing),
        "duplicates": len(duplicates),
        "transaction_count": len(all_rows),
        "by_category": dict(sorted(by_category.items())),
    }


def exceptions(ledger: dict) -> dict:
    rows = transactions(ledger)
    return {
        "missing_receipts": [r for r in rows if r.get("needs_receipt")],
        "duplicates": [r for r in rows if r.get("duplicate_of")],
        "delta_cents": int(ledger.get("meta", {}).get("reconciled_delta_cents", 0)),
    }


def evidence_index(ledger: dict) -> list[dict]:
    return [
        {
            "transaction_id": r["id"],
            "date": r["date"],
            "vendor": r["vendor"],
            "amount_cents": r["amount_cents"],
            "source_message_id": r.get("source_message_id"),
            "source_quote": r.get("source_quote", ""),
        }
        for r in transactions(ledger)
        if r.get("source_message_id")
    ]
