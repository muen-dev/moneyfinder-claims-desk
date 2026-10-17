"""Analysis orchestrator: one run = one PRISM session; every step is a real span.

If PRISM span instrumentation is available (``app.services.tracing``) each step is
an OpenTelemetry tool span under one agent span, so PRISM gets tool calls and
token usage. If it is not, the older HTTP summary emitter is used as a fallback.
"""
from __future__ import annotations

import json
import time
from contextlib import nullcontext
from datetime import UTC, datetime

from flask import current_app

from ..util import now_iso
from . import eligibility, evidence, ledger, packet
from .nicrron import Nicrron
from .tracing import annotate

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


def _tracing():
    try:
        return current_app.extensions.get("tracing")
    except RuntimeError:
        return None


def start_run(store, prism) -> dict:
    run_id = _run_id()
    started = now_iso()
    steps: list[dict] = []
    failed = False
    tracing = _tracing()
    use_spans = bool(tracing and tracing.is_enabled())
    exported_before = tracing.exported if tracing else 0

    parent = tracing.span(
        "analysis_run", run_id, span_type="agent",
        input_text=f"{store.business.get('legal_name', 'demo')} · 12-step analysis",
        attributes={"gen_ai.agent.name": "moneyfinder-backoffice"},
    ) if use_spans else nullcontext()

    with parent as root_span:
        def step(name: str, tool: str, fn, gate: bool = False):
            nonlocal failed
            t0 = time.perf_counter()
            status, summary = "succeeded", ""
            error = None
            ctx = tracing.span(
                name, run_id, span_type="tool", tool=tool,
                input_text=f"{store.business.get('legal_name', 'demo')} · {name}",
            ) if use_spans else nullcontext()
            with ctx as span:
                try:
                    summary = fn()
                except Exception as exc:  # noqa: BLE001 - a failed tool must not fabricate a finding
                    status, error = "failed", f"{type(exc).__name__}: {exc}"
                    failed = True
                    summary = error
                if gate and not failed:
                    status = "pending"
                latency = int((time.perf_counter() - t0) * 1000)
                annotate(span, output_text=str(summary)[:1500], status=status,
                         **({"error": error} if error else {}))
                if not use_spans:
                    recorded = prism.emit(
                        session_id=run_id, step=name, tool=tool, status=status,
                        latency_ms=latency,
                        input_summary=f"{store.business.get('legal_name', 'demo')} · {name}",
                        output_summary=str(summary)[:500], error=error,
                    )
                    steps.append(
                        {"step": name, "tool": tool, "status": status, "latency_ms": latency,
                         "input_summary": f"{name} on demo dataset",
                         "output_summary": str(summary)[:500], "error": error,
                         "prism_delivered": recorded}
                    )
                else:
                    steps.append(
                        {"step": name, "tool": tool, "status": status, "latency_ms": latency,
                         "input_summary": f"{name} on demo dataset",
                         "output_summary": str(summary)[:500], "error": error,
                         "prism_delivered": True}
                    )
                return summary

        scan = step("gmail_scan", "scan_inbox", lambda: evidence.scan(store)["stats"])
        step("extract_facts", "extract_facts", lambda: f"{len(evidence.profile_facts(store))} facts with excerpts")
        step("extract_purchases", "extract_purchases", lambda: f"{len(store.ledger.get('transactions', []))} transactions")
        step("categorize_ledger", "categorize_ledger", lambda: f"{len(ledger.summary(store.ledger)['by_category'])} categories")
        step("reconcile_ledger", "reconcile_ledger", lambda: ledger.summary(store.ledger))
        step("program_candidates", "find_candidates", lambda: f"{len(store.programs)} programs from the catalog")
        step("agency_fetch", "fetch_program_page", lambda: f"{sum(1 for p in store.programs if p.get('source_excerpt'))} cached official pages")

        def eligibility_extract():
            counts = eligibility.verdicts(store)["counts"]
            nicrron = Nicrron()
            if not nicrron.enabled:
                return {"mode": "deterministic", "counts": counts}
            programs = [{"id": p["id"], "verdict": p["verdict"],
                         "excerpt": (p.get("source_excerpt") or "")[:180]}
                        for p in store.programs]
            prompt = "Programs: " + json.dumps(programs) + ' Return {"eligible":[ids],"needs_info":[ids],"expired":[ids]}.'
            llm_ctx = tracing.span(
                "nicrron.eligibility_extract", run_id, span_type="llm",
                model=nicrron.model, input_text=prompt,
            ) if use_spans else nullcontext()
            with llm_ctx as llm_span:
                result = nicrron.complete_json(
                    "You are an eligibility evidence reviewer. Return strict JSON only; never add a program id.",
                    prompt,
                )
                usage = result.get("usage", {}) or {}
                annotate(llm_span, model=result.get("model"),
                         tokens_in=usage.get("prompt_tokens"),
                         tokens_out=usage.get("completion_tokens"),
                         output_text=json.dumps(result.get("data", {}))[:1500])
            valid = {p["id"] for p in store.programs}
            data = result.get("data", {})
            model_verdicts = {k: [i for i in v if i in valid] for k, v in data.items() if isinstance(v, list)}
            return {"mode": "nicrron", "model": result.get("model"), "counts": counts,
                    "model_verdicts": model_verdicts}

        step("eligibility_extract", "extract_eligibility", eligibility_extract)
        step("match_score", "score_match", lambda: f"{eligibility.verdicts(store)['counts'].get('eligible', 0)} eligible verdicts")
        step("form_prep", "prepare_application", lambda: f"{len(store.applications)} applications prepared")
        step("human_approve", "request_approval", lambda: "awaiting human approval before any submission", gate=True)
        built = step("build_accountant_packet", "build_accountant_packet", lambda: len(packet.build(store)["files"]))

        if use_spans:
            annotate(root_span, output_text=f"12 steps · {len(steps)} recorded · failed={failed}")

    if tracing:
        tracing.flush()
    span_exported = bool(tracing and tracing.exported > exported_before)
    telemetry = "ok" if (span_exported or prism.emitted > 0) else "pending"
    if not span_exported and not prism.emitted:
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
