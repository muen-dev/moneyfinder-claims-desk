"""JSON API — the contract the UI (and teammates) build against."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file

from ..services import applications, eligibility, evidence, ledger, packet
from ..services.nicrron import Nicrron
from ..services.orchestrator import start_run
from ..services.prism import Prism

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
