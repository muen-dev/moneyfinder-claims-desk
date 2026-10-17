"""HTML pages."""
from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ..services import applications, eligibility, evidence, ledger, packet
from ..services.nicrron import Nicrron
from ..services.orchestrator import start_run
from ..services.prism import Prism

bp = Blueprint("pages", __name__)


def store():
    return current_app.extensions["store"]


def services():
    return Nicrron(), Prism()


@bp.get("/")
def home():
    return redirect(url_for("pages.dashboard"))


@bp.get("/dashboard")
def dashboard():
    s = store()
    pipe = applications.pipeline(s.applications)
    return render_template(
        "dashboard.html",
        business=s.business,
        pipe=pipe,
        runs=s.runs[:4],
        integrations=[services()[0].status(), services()[1].status()],
    )


@bp.get("/onboarding")
def onboarding():
    s = store()
    return render_template("onboarding.html", business=s.business, scan=None)


@bp.post("/onboarding/scan")
def onboarding_scan():
    s = store()
    scan = evidence.scan(s)
    return render_template("onboarding.html", business=s.business, scan=scan)


@bp.get("/eligibility")
def eligibility_page():
    s = store()
    return render_template("eligibility.html", verdicts=eligibility.verdicts(s))


@bp.get("/books")
def books():
    s = store()
    return render_template(
        "books.html",
        summary=ledger.summary(s.ledger),
        exceptions=ledger.exceptions(s.ledger),
        transactions=ledger.transactions(s.ledger),
        packet=s.packet,
    )


@bp.post("/books/packet")
def books_packet():
    s = store()
    pkt = packet.build(s)
    flash(f"Packet prepared: {len(pkt['files'])} files. Prepared for professional review, not filed.")
    return redirect(url_for("pages.books"))


@bp.get("/run-history")
def run_history():
    s = store()
    return render_template("run_history.html", runs=s.runs, integrations=[services()[1].status()])


@bp.post("/run")
def run_analysis():
    s = store()
    nicrron, prism = services()
    run = start_run(s, prism)
    flash(f"Run {run['id']} · {run['status']} · PRISM telemetry {run['telemetry']}.")
    return redirect(url_for("pages.run_history"))


@bp.get("/settings")
def settings():
    s = store()
    nicrron, prism = services()
    return render_template(
        "settings.html",
        business=s.business,
        integrations=[nicrron.status(), prism.status()],
        nicrron_enabled=nicrron.enabled,
        prism_enabled=prism.enabled,
    )


@bp.post("/settings/reset")
def settings_reset():
    store().reset()
    flash("Demo state reset to fixtures.")
    return redirect(url_for("pages.settings"))


@bp.get("/applications/<app_id>")
def application_detail(app_id: str):
    s = store()
    app = s.application(app_id)
    if app is None:
        return ("Application not found", 404)
    allowed = applications.ALLOWED.get(app.get("status"), set())
    events = [e for e in s.events if e["application_id"] == app_id]
    app["column"] = applications.COLUMNS.get(app.get("status"), "closed")
    return render_template("application.html", app=app, allowed=sorted(allowed), events=events)


@bp.post("/applications/<app_id>/transition")
def application_transition(app_id: str):
    s = store()
    to_status = request.form.get("to_status", "")
    try:
        if to_status == "PAYMENT_CONFIRMED":
            s.confirm_deposit(app_id, actor="user")
        else:
            s.transition(app_id, to_status, actor="user", note="Manual transition from the desk")
        flash(f"{app_id} moved to {to_status}.")
    except Exception as exc:  # noqa: BLE001
        flash(f"Transition failed: {exc}")
    return redirect(url_for("pages.application_detail", app_id=app_id))
