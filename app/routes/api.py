"""JSON API — the contract the UI (and teammates) build against."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file

from ..services import applications, eligibility, evidence, ledger, packet
from ..services.prism import Prism
from ..services.tracing import annotate
from ..services.nicrron import Nicrron
from ..services.orchestrator import start_run
from ..services.prism import Prism
from ..services.tracing import annotate

bp = Blueprint("api", __name__)


def store():
    return current_app.extensions["store"]


def services():
    return Nicrron(), Prism()


def ok(**payload):
    payload.setdefault("synthetic", True)
    return jsonify(payload)


@bp.get("/health")
def health():
    return ok(ok=True, mode="demo", business=store().business.get("legal_name"))


@bp.post("/demo/reset")
def reset():
    store().reset()
    return ok(ok=True, reset_at=store().reset_at)


@bp.get("/profile")
def profile():
    s = store()
    return ok(business=s.business, facts=s.profile.get("facts", []),
              conflicts=s.profile.get("conflicts", []))


@bp.get("/inbox")
def inbox():
    s = store()
    return ok(messages=evidence.messages(s, q=request.args.get("q", ""),
                                         category=request.args.get("category", "")))


@bp.get("/messages/<message_id>")
def message(message_id: str):
    s = store()
    msg = evidence.message(s, message_id)
    if msg is None:
        return jsonify({"error": {"code": "not_found", "message": "message not found"}}), 404
    return ok(message=msg)


@bp.get("/applications")
def applications_list():
    s = store()
    pipe = applications.pipeline(s.applications)
    return ok(applications=pipe["columns"], totals=pipe["totals"], count=pipe["count"])


@bp.get("/applications/<app_id>")
def application_detail(app_id: str):
    s = store()
    app = s.application(app_id)
    if app is None:
        return jsonify({"error": {"code": "not_found", "message": "application not found"}}), 404
    events = [e for e in s.events if e["application_id"] == app_id]
    return ok(application=app, events=events)


@bp.post("/applications/<app_id>/transition")
def application_transition(app_id: str):
    s = store()
    payload = request.get_json(silent=True) or {}
    to_status = payload.get("to_status", "")
    try:
        if to_status == "PAYMENT_CONFIRMED":
            app = s.confirm_deposit(app_id, actor=payload.get("actor", "agent"))
        else:
            app = s.transition(app_id, to_status, actor=payload.get("actor", "agent"),
                               note=payload.get("note", ""))
        return ok(application=app)
    except KeyError as exc:
        return jsonify({"error": {"code": "not_found", "message": str(exc)}}), 404
    except ValueError as exc:
        return jsonify({"error": {"code": "invalid_transition", "message": str(exc)}}), 400


@bp.get("/eligibility")
def eligibility_verdicts():
    s = store()
    return ok(**eligibility.verdicts(s))


@bp.get("/ledger")
def ledger_data():
    s = store()
    return ok(summary=ledger.summary(s.ledger), transactions=ledger.transactions(s.ledger),
              exceptions=ledger.exceptions(s.ledger))


@bp.get("/ledger/exceptions")
def ledger_exceptions():
    return ok(**ledger.exceptions(store().ledger))


@bp.post("/ledger/packet")
def build_packet():
    pkt = packet.build(store())
    return ok(packet={k: v for k, v in pkt.items() if k != "markdown"}, markdown=pkt["markdown"])


@bp.get("/ledger/packet/<packet_id>/<filename>")
def download_packet(packet_id: str, filename: str):
    from ..services.packet import PACKET_ID

    if packet_id != PACKET_ID:
        return jsonify({"error": {"code": "not_found", "message": "packet not found"}}), 404
    path = store().data / "packets" / PACKET_ID / filename
    if not path.exists():
        return jsonify({"error": {"code": "not_found", "message": "file not found"}}), 404
    return send_file(path, as_attachment=True, download_name=filename)


@bp.post("/analysis/run")
def analysis_run():
    s = store()
    _, prism = services()
    return ok(run=start_run(s, prism))


@bp.get("/runs")
def runs():
    return ok(runs=store().runs)


@bp.get("/runs/<run_id>")
def run_detail(run_id: str):
    run = next((r for r in store().runs if r["id"] == run_id), None)
    if run is None:
        return jsonify({"error": {"code": "not_found", "message": "run not found"}}), 404
    return ok(run=run)


@bp.get("/integrations/status")
def integrations():
    nicrron, prism = services()
    return ok(integrations=[nicrron.status(), prism.status(),
                            {"name": "ElevenLabs", "status": "unavailable", "detail": "P1 — not configured"}])


@bp.get("/voice/summary")
def voice_summary():
    s = store()
    pipe = applications.pipeline(s.applications)
    t = pipe["totals"]
    text = (
        f"{s.business.get('legal_name', 'This business')} has {pipe['count']} applications: "
        f"{len(pipe['columns']['in_process'])} in process, {len(pipe['columns']['approved'])} approved, "
        f"{len(pipe['columns']['paid'])} paid. Identified estimate is not money received. "
        "The next action is to review the exception queue."
    )
    return ok(text=text, totals=t)


# ---- onboarding (3-phase flow) -------------------------------------

def _emit(step: str, tool: str, summary: str = "") -> None:
    from flask import session
    run_id = session.get("onboarding_run_id")
    if not run_id or current_app.config.get("TESTING"):
        return
    tracing = current_app.extensions.get("tracing")
    if tracing and tracing.is_enabled():
        with tracing.span(step, run_id, span_type="tool", tool=tool,
                          input_text=f"onboarding · {step}", output_text=summary or step) as span:
            annotate(span, status="ok", output_text=summary or step)
        return
    Prism().emit(session_id=run_id, step=step, tool=tool, status="ok",
                 input_summary=f"onboarding · {step}", output_summary=summary or step)


@bp.get("/onboarding/profile")
def onboarding_profile():
    s = store()
    return ok(fields=s.onboarding_fields(), missing_required=s.missing_required(),
              stats={"messages": len(s.profile.get("messages", [])), "facts": len(s.profile.get("facts", [])),
                     "conflicts": len(s.profile.get("conflicts", [])), "purchases": len(s.ledger.get("transactions", []))})


@bp.get("/onboarding/benefits")
def onboarding_benefits():
    s = store()
    s.mark_benefits_ready()
    _emit("benefit_search", "search_programs", f"{len(s.benefits())} programs with citations")
    _emit("benefit_match", "score_match", "fit scores computed from profile signals")
    return ok(benefits=s.benefits())


@bp.post("/onboarding/benefits/<benefit_id>/fill")
def onboarding_fill(benefit_id: str):
    s = store()
    benefit = s.benefit(benefit_id)
    if benefit is None:
        return jsonify({"error": {"code": "not_found", "message": "benefit not found"}}), 404
    s.select_benefit(benefit_id)
    _emit("pdf_fetch", "fetch_pdf_form", f"{benefit['form']} from {benefit['agency']}")
    _emit("form_fill", "fill_form", f"{len(benefit['form_fields'])} fields")
    return ok(benefit=benefit, fields=benefit["form_fields"])


@bp.post("/onboarding/benefits/<benefit_id>/submit")
def onboarding_submit(benefit_id: str):
    s = store()
    payload = request.get_json(silent=True) or {}
    if not payload.get("approved"):
        return jsonify({"error": {"code": "approval_required", "message": "approve the filled form first"}}), 400
    try:
        app = s.submit_benefit(benefit_id, actor="user")
    except KeyError as exc:
        return jsonify({"error": {"code": "not_found", "message": str(exc)}}), 404
    _emit("user_approval", "request_approval", "user approved")
    _emit("submit", "mock_submit", app.get("confirmation_id", ""))
    _emit("status_check", "poll_status", "submitted")
    return ok(application=app)
