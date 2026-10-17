"""Analysis orchestrator: one run = one PRISM session; every step is recorded honestly."""
from __future__ import annotations

import time
from datetime import UTC, datetime

from ..util import now_iso
from . import eligibility, evidence, ledger, packet

STEP_TOOLS = [
    ("gmail_scan", "scan_inbox"),
    ("extract_facts", "extract_facts"),
    ("extract_purchases", "extract_purchases"),
    ("categorize_ledger", "categorize_ledger"),
    ("reconcile_ledger", "reconcile_ledger"),
    ("program_candidates", "find_candidates"),
    ("agency_fetch", "fetch_program_page"),
    ("eligibility_extract", "extract_eligibility"),
    ("match_score", "score_match"),
    ("form_prep", "prepare_application"),
    ("human_approve", "request_approval"),
    ("build_accountant_packet", "build_accountant_packet"),
]


def _run_id() -> str:
    return "run_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def start_run(store, prism) -> dict:
    run_id = _run_id()
    started = now_iso()
    steps: list[dict] = []
    failed = False
    prism_attempted = 0

    def step(name: str, tool: str, fn, gate: bool = False):
        nonlocal failed, prism_attempted
        t0 = time.perf_counter()
        status, summary = "succeeded", ""
        error = None
        try:
            summary = fn()
        except Exception as exc:  # noqa: BLE001 - a failed tool must not fabricate a finding
            status, error = "failed", f"{type(exc).__name__}: {exc}"
            failed = True
            summary = error
        if gate and not failed:
            status = "pending"
        latency = int((time.perf_counter() - t0) * 1000)
        emitted = prism.emit(
            session_id=run_id, step=name, tool=tool, status=status, latency_ms=latency,
            input_summary=f"{store.business.get('legal_name', 'demo')} · {name}",
            output_summary=str(summary)[:500], error=error,
        )
        prism_attempted += 1 if prism.enabled else 0
        steps.append(
            {"step": name, "tool": tool, "status": status, "latency_ms": latency,
             "input_summary": f"{name} on demo dataset", "output_summary": str(summary)[:500],
             "error": error, "prism_delivered": emitted}
        )
        return summary

    scan = step("gmail_scan", "scan_inbox", lambda: evidence.scan(store)["stats"])
    step("extract_facts", "extract_facts", lambda: f"{len(evidence.profile_facts(store))} facts with excerpts")
    step("extract_purchases", "extract_purchases", lambda: f"{len(store.ledger.get('transactions', []))} transactions")
    step("categorize_ledger", "categorize_ledger", lambda: f"{len(ledger.summary(store.ledger)['by_category'])} categories")
    step("reconcile_ledger", "reconcile_ledger", lambda: ledger.summary(store.ledger))
    step("program_candidates", "find_candidates", lambda: f"{len(store.programs)} programs from the catalog")
    step("agency_fetch", "fetch_program_page", lambda: f"{sum(1 for p in store.programs if p.get('source_excerpt'))} cached official pages")
    step("eligibility_extract", "extract_eligibility", lambda: eligibility.verdicts(store)["counts"])
    step("match_score", "score_match", lambda: f"{eligibility.verdicts(store)['counts'].get('eligible', 0)} eligible verdicts")
    step("form_prep", "prepare_application", lambda: f"{len(store.applications)} applications prepared")
    step("human_approve", "request_approval", lambda: "awaiting human approval before any submission", gate=True)
    built = step("build_accountant_packet", "build_accountant_packet", lambda: len(packet.build(store)["files"]))

    telemetry = "ok" if (not prism.enabled or prism.emitted > 0) else "pending"
    if not prism.enabled:
        telemetry = "pending"
    run = {
        "id": run_id,
        "case_id": "case_gowanus_2025",
        "version": "v1",
        "status": "partial" if failed else "succeeded",
        "started_at": started,
        "ended_at": now_iso(),
        "steps": steps,
        "telemetry": telemetry,
        "prism_session_id": run_id,
        "prism_url": None,
        "error": None,
        "awaiting_approval": True,
        "summary": {"facts": len(evidence.profile_facts(store)),
                    "transactions": len(store.ledger.get("transactions", [])),
                    "programs": len(store.programs), "packet_files": built},
        "scan_stats": scan,
    }
    store.add_run(run)
    return run
