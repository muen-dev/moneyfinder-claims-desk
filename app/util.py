"""Small helpers used across the app."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def money(cents: int | None) -> str:
    if cents is None:
        return "—"
    return f"${cents / 100:,.0f}"


def plain(amount_cents: int) -> str:
    return f"{amount_cents / 100:,.2f}"
