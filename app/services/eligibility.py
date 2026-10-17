"""Eligibility verdicts from the curated program fixture.

The demo uses cached official-page excerpts (as_of) so it works offline; a live
official-domain fetch can replace `load_programs` later without changing the shape.
"""
from __future__ import annotations

OFFICIAL_HOSTS = ("tax.ny.gov", "irs.gov", "ny.gov", "nyc.gov", "nyserda.ny.gov", "coned.com")


def load_programs(store) -> list[dict]:
    return list(store.programs)


def verdicts(store) -> dict:
    programs = load_programs(store)
    counts = {"eligible": 0, "needs_info": 0, "not_eligible": 0, "expired": 0}
    for p in programs:
        counts[p.get("verdict", "needs_info")] = counts.get(p.get("verdict", "needs_info"), 0) + 1
    return {"programs": programs, "counts": counts, "total": len(programs)}


def summary_line(program: dict) -> str:
    verdict = program.get("verdict", "needs_info")
    if verdict == "expired":
        return "Expired — do not open an application"
    if verdict == "eligible":
        return "Evidence supports eligibility — review before filing"
    if verdict == "needs_info":
        return "One question to resolve"
    return "Not eligible on this profile"
