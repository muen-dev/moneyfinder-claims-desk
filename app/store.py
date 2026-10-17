"""Demo state loaded from fixtures; reset restores it. JSON only — no external services required."""
from __future__ import annotations

import copy
import json
import threading
from pathlib import Path

from .util import load_json, now_iso, write_json

FIXTURE_FILES = {
    "business": "business.json",
    "profile": "profile.json",
    "applications": "applications.json",
    "programs": "programs.json",
    "ledger": "ledger.json",
    "runs": "runs.json",
}


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.fixtures = self.root / "fixtures"
        self.data = self.root / "data"
        self.lock = threading.RLock()
        self.reset()

    def load(self) -> None:
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.business = load_json(self.fixtures / FIXTURE_FILES["business"], {}) or {}
            self.profile = load_json(self.fixtures / FIXTURE_FILES["profile"], {}) or {}
            self.applications = load_json(self.fixtures / FIXTURE_FILES["applications"], []) or []
            self.programs = load_json(self.fixtures / FIXTURE_FILES["programs"], []) or []
            self.ledger = load_json(self.fixtures / FIXTURE_FILES["ledger"], []) or []
            self.runs = load_json(self.fixtures / FIXTURE_FILES["runs"], []) or []
            self.events = []
            self.tasks = []
            self.packet = None
            self.reset_at = now_iso()
            self._persist()

    def _persist(self) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        write_json(
            self.data / "state.json",
            {
                "reset_at": self.reset_at,
                "applications": self.applications,
                "events": self.events,
                "tasks": self.tasks,
                "runs": self.runs,
            },
        )

    # ---- applications -------------------------------------------------
    def application(self, app_id: str):
        return next((a for a in self.applications if a.get("id") == app_id), None)

    def transition(self, app_id: str, to_status: str, actor: str = "agent", note: str = ""):
        from .services.applications import COLUMNS, STATUSES, transition_allowed

        with self.lock:
            app = self.application(app_id)
            if app is None:
                raise KeyError(f"unknown application {app_id}")
            frm = app.get("status")
            if to_status not in STATUSES:
                raise ValueError(f"unknown status {to_status}")
            if not transition_allowed(frm, to_status):
                raise ValueError(f"illegal transition {frm} -> {to_status}")
            app["status"] = to_status
            app["column"] = COLUMNS[to_status]
            app["updated_at"] = now_iso()
            self.events.append(
                {
                    "id": f"evt_{len(self.events) + 1:04d}",
                    "application_id": app_id,
                    "from_status": frm,
                    "to_status": to_status,
                    "actor": actor,
                    "note": note,
                    "at": now_iso(),
                }
            )
            self._persist()
            return app

    def confirm_deposit(self, app_id: str, actor: str = "agent") -> dict:
        """PAYMENT_CONFIRMED requires a matched mock deposit, never the agency claim alone."""
        with self.lock:
            app = self.application(app_id)
            if app is None:
                raise KeyError(f"unknown application {app_id}")
            if app.get("status") != "PAYMENT_ISSUED":
                raise ValueError("deposit can only be confirmed after PAYMENT_ISSUED")
            return self.transition(app_id, "PAYMENT_CONFIRMED", actor=actor,
                                   note="Mock bank deposit matched amount + reference (synthetic)")

    # ---- runs ---------------------------------------------------------
    def add_run(self, run: dict) -> dict:
        with self.lock:
            self.runs.insert(0, run)
            self.runs = self.runs[:25]
            self._persist()
            return run

    # ---- tasks --------------------------------------------------------
    def add_task(self, task: dict) -> dict:
        with self.lock:
            self.tasks.insert(0, task)
            self._persist()
            return task

    def as_dict(self) -> dict:
        return {
            "business": self.business,
            "profile": self.profile,
            "applications": self.applications,
            "programs": self.programs,
            "ledger": self.ledger,
            "runs": self.runs,
            "events": self.events,
            "tasks": self.tasks,
        }
