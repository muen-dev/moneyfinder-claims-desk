"""Inbox/evidence helpers: source-linked facts, categories, and conflicts."""
from __future__ import annotations

import re
from collections import Counter

CATEGORIES = ["tax-credit", "audit", "legal", "administrative", "unrelated"]

_CATEGORY_RULES = [
    ("tax-credit", re.compile(r"tax credit|WOTC|work opportunity|hire a veteran|DTF|Department of Taxation|IRS|tips|R&D|research credit", re.I)),
    ("audit", re.compile(r"audit|notice of deficiency|examination", re.I)),
    ("legal", re.compile(r"legal|attorney|counsel|lawsuit|subpoena", re.I)),
    ("administrative", re.compile(r"payroll|invoice|statement|license|permit|insurance|accountant|renewal|onboarding complete|financing|bill", re.I)),
]


def categorize(message: dict) -> str:
    text = f"{message.get('subject', '')} {message.get('snippet', '')} {message.get('body', '')[:500]}"
    for category, pattern in _CATEGORY_RULES:
        if pattern.search(text):
            return category
    return "unrelated"


def messages(store, q: str = "", category: str = "") -> list[dict]:
    rows = []
    for m in store.profile.get("messages", []):
        row = dict(m)
        row.setdefault("category", categorize(row))
        if q and q.lower() not in f"{row.get('subject', '')} {row.get('sender', '')}".lower():
            continue
        if category and row["category"] != category:
            continue
        rows.append(row)
    return rows


def message(store, message_id: str) -> dict | None:
    for m in store.profile.get("messages", []):
        if m.get("id") == message_id:
            row = dict(m)
            row.setdefault("category", categorize(row))
            return row
    return None


def scan(store) -> dict:
    profile = store.profile
    facts = profile.get("facts", [])
    conflicts = profile.get("conflicts", [])
    msgs = messages(store)
    counts = Counter(m["category"] for m in msgs)
    return {
        "business": store.business,
        "messages": msgs,
        "facts": facts,
        "conflicts": conflicts,
        "stats": {
            "messages": len(msgs),
            "facts": len(facts),
            "conflicts": len(conflicts),
            "purchases": len(store.ledger.get("transactions", [])),
            "categories": dict(counts),
            "missing_attachments": sum(1 for m in msgs if m.get("attachment_state") == "missing"),
        },
    }


def profile_facts(store) -> list[dict]:
    return store.profile.get("facts", [])
