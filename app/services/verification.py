"""Brewery verification: SLA license, DOS standing, NYC zoning/BBL, tax classification.

Adapted from Kenan's Moneyfinder Verification Engine (AI Studio). The demo uses a
synthetic registry snapshot in ``fixtures/verification.json``; the shape matches
the values the engine checks against NYS SLA, NYS DOS, NYC Open Data and the
federal tax classification.
"""
from __future__ import annotations

from pathlib import Path

from ..util import load_json


def results(store) -> dict:
    data = load_json(Path(store.root) / "fixtures" / "verification.json", {}) or {}
    profile = {f["key"]: (f.get("value") or "") for f in store.onboarding_fields()}
    inputs = dict(data.get("inputs", {}))
    inputs["legal_name"] = profile.get("legal_name") or inputs.get("legal_name", "")
    inputs["address"] = profile.get("address") or inputs.get("address", "")
    inputs["ein"] = profile.get("ein") or ""
    if profile.get("entity_type"):
        inputs["entity_type"] = profile["entity_type"]
    data["inputs"] = inputs
    data["verified"] = all(c.get("status") == "verified" for c in data.get("checks", []))
    return data


def summary(store) -> dict:
    data = results(store)
    return {
        "verified": data["verified"],
        "checks": len([c for c in data.get("checks", []) if c.get("status") == "verified"]),
        "incentives": len(data.get("incentives", [])),
        "source": "Synthetic registry snapshot (SLA · DOS · NYC Open Data · tax classification)",
    }
