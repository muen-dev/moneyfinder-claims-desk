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
    "onboarding": "onboarding.json",
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
            self.onboarding_fixture = load_json(self.fixtures / FIXTURE_FILES["onboarding"], {}) or {}
            self.onboarding = {
                "gmail_connected": False,
                "gmail_scanned": False,
                "profile_saved": False,
                "benefits_ready": False,
                "selected_benefit": None,
                "filled_benefit": None,
                "filled_pdf": None,
                "application_id": None,
                "fields": copy.deepcopy(self.onboarding_fixture.get("profile_fields", [])),
                "run_id": None,
            }
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
                "onboarding": self.onboarding,
            },
        )

    # ---- onboarding ---------------------------------------------------
    def onboarding_fields(self) -> list[dict]:
        return self.onboarding["fields"]

    def missing_required(self) -> list[dict]:
        return [f for f in self.onboarding_fields() if f.get("required") and not (f.get("value") or "").strip()]

    def save_onboarding_profile(self, values: dict) -> list[dict]:
        with self.lock:
            for field in self.onboarding_fields():
                if field["key"] in values:
                    field["value"] = (values[field["key"]] or "").strip()
                    field["source"] = "You edited this"
                    field["confidence"] = 1.0
            missing = self.missing_required()
            self.onboarding["profile_saved"] = len(missing) == 0
            self._persist()
            return missing

    def benefits(self) -> list[dict]:
        return self.onboarding_fixture.get("benefits", [])

    def mark_gmail_scanned(self) -> None:
        self.onboarding["gmail_scanned"] = True
        self._persist()

    def mark_benefit_filled(self, benefit_id: str, pdf_path: str, field_count: int) -> None:
        self.onboarding["filled_benefit"] = benefit_id
        self.onboarding["filled_pdf"] = pdf_path
        self.onboarding["filled_field_count"] = field_count
        self._persist()

    def benefit(self, benefit_id: str) -> dict | None:
        return next((b for b in self.benefits() if b.get("id") == benefit_id), None)

    def mark_benefits_ready(self) -> None:
        self.onboarding["benefits_ready"] = True
        self._persist()

    def select_benefit(self, benefit_id: str) -> dict:
        benefit = self.benefit(benefit_id)
        if benefit is None:
            raise KeyError(f"unknown benefit {benefit_id}")
        self.onboarding["selected_benefit"] = benefit_id
        self._persist()
        return benefit

    def submit_benefit(self, benefit_id: str, actor: str = "user") -> dict:
        from .services.applications import transition_allowed

        with self.lock:
            benefit = self.benefit(benefit_id)
            if benefit is None:
                raise KeyError(f"unknown benefit {benefit_id}")
            app = next((a for a in self.applications if a.get("program_id") == benefit["program_id"]), None)
            if app is None:
                app = {
                    "id": f"app_{benefit_id}",
                    "program_id": benefit["program_id"],
                    "program": benefit["name"],
                    "form": benefit["form"],
                    "agency": benefit["agency"],
                    "amount_estimate_cents": benefit["amount_estimate_cents"],
                    "amount_type": "estimate",
                    "status": "MATCH_FOUND",
                    "next_action": "Review and approve the form",
                    "deadline": benefit.get("deadline"),
                    "expected_by": None,
                    "confidence": 0.9,
                    "source_url": benefit.get("source_url"),
                    "evidence": [{"kind": "profile", "ref": "onboarding", "excerpt": benefit.get("why_fit", "")}],
                }
                self.applications.append(app)
            chain = []
            if app["status"] == "MATCH_FOUND":
                chain = ["FORM_READY", "USER_APPROVED", "SUBMITTED"]
            elif app["status"] == "FORM_READY":
                chain = ["USER_APPROVED", "SUBMITTED"]
            elif app["status"] == "USER_APPROVED":
                chain = ["SUBMITTED"]
            for status in chain:
                if transition_allowed(app["status"], status):
                    self.transition(app["id"], status, actor=actor, note="Submitted from onboarding")
            app.update({
                "form": benefit["form"],
                "program": benefit["name"],
                "agency": benefit["agency"],
                "amount_estimate_cents": benefit["amount_estimate_cents"],
                "next_action": "Agency review — check back in 5–10 business days",
                "submitted_at": now_iso(),
                "confirmation_id": f"NY-DEMO-{benefit['form']}-1042",
                "progress": 40,
                "progress_steps": benefit.get("progress_steps", []),
                "selected_benefit": benefit_id,
            })
            self.onboarding["selected_benefit"] = benefit_id
            self.onboarding["application_id"] = app["id"]
            self._persist()
            return app

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
