"""Public landing, demo auth, and the three-phase agent onboarding."""
from __future__ import annotations

import time

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, session, url_for

from ..auth import current_user, login_required
from ..services import pdf_fill
from ..services.prism import Prism
from ..services.tracing import annotate

bp = Blueprint("flow", __name__)

DEMO_EMAIL = "marisol@gowanuskettle.example"


def store():
    return current_app.extensions["store"]


def emit(step: str, tool: str, status: str = "succeeded", summary: str = "") -> None:
    run_id = session.get("onboarding_run_id")
    if not run_id or current_app.config.get("TESTING"):
        return
    tracing = current_app.extensions.get("tracing")
    if tracing and tracing.is_enabled():
        with tracing.span(
            step, run_id, span_type="tool", tool=tool,
            input_text=f"onboarding · {step}", output_text=summary or step,
        ) as span:
            annotate(span, status="ok" if status == "succeeded" else status,
                     output_text=summary or step)
        return
    Prism().emit(
        session_id=run_id,
        step=step,
        tool=tool,
        status="ok" if status == "succeeded" else status,
        input_summary=f"onboarding · {step}",
        output_summary=summary or step,
    )


@bp.get("/")
def landing():
    return render_template("landing.html", user=current_user())


@bp.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        if "@" not in email:
            flash("Enter an email address to continue (demo only).")
            return render_template("signin.html"), 400
        session["user"] = {"email": email, "name": "Marisol Vance"}
        session.setdefault("onboarding_run_id", f"onboard_{int(time.time())}")
        nxt = request.args.get("next") or request.form.get("next") or url_for("flow.onboarding")
        return redirect(nxt)
    if current_user():
        return redirect(url_for("flow.onboarding"))
    return render_template("signin.html", next=request.args.get("next", ""))


@bp.get("/signout")
def signout():
    session.clear()
    return redirect(url_for("flow.landing"))


@bp.get("/onboarding")
@login_required
def onboarding():
    s = store()
    if not s.onboarding["gmail_connected"]:
        return redirect(url_for("flow.connect"))
    if not s.onboarding["profile_saved"]:
        return redirect(url_for("flow.profile_review"))
    if not s.onboarding["benefits_ready"]:
        return redirect(url_for("flow.searching"))
    if s.onboarding.get("application_id"):
        return redirect(url_for("flow.progress", app_id=s.onboarding["application_id"]))
    if not s.onboarding["selected_benefit"]:
        return redirect(url_for("flow.benefits"))
    return redirect(url_for("flow.benefit_detail", benefit_id=s.onboarding["selected_benefit"]))


@bp.get("/onboarding/connect")
@login_required
def connect():
    if store().onboarding["gmail_connected"]:
        return redirect(url_for("flow.profile_review"))
    return render_template("onboarding_connect.html", step=1)


@bp.post("/onboarding/connect")
@login_required
def connect_submit():
    s = store()
    s.onboarding["gmail_connected"] = True
    if not session.get("onboarding_run_id"):
        session["onboarding_run_id"] = f"onboard_{int(time.time())}"
    emit("gmail_permission", "request_gmail_scope", "succeeded", "Read-only synthetic mailbox")
    emit("gmail_scan", "scan_inbox", "succeeded", "25 synthetic messages")
    flash("Synthetic mailbox connected (read-only). Building your profile…")
    return redirect(url_for("flow.profile_loading"))


@bp.get("/onboarding/profile-loading")
@login_required
def profile_loading():
    if not store().onboarding["gmail_connected"]:
        return redirect(url_for("flow.connect"))
    return render_template("profile_loading.html", step=1)


@bp.get("/onboarding/profile")
@login_required
def profile_review():
    s = store()
    if not s.onboarding["gmail_connected"]:
        return redirect(url_for("flow.connect"))
    return render_template("profile_review.html", step=1, fields=s.onboarding_fields(),
                           missing=s.missing_required(), error=None)


@bp.post("/onboarding/profile")
@login_required
def profile_save():
    s = store()
    values = {f["key"]: request.form.get(f"field_{f['key']}", "") for f in s.onboarding_fields()}
    missing = s.save_onboarding_profile(values)
    if missing:
        return render_template("profile_review.html", step=1, fields=s.onboarding_fields(),
                               missing=missing, error="Fill the coral fields to continue.")
    emit("profile_build", "build_profile", "succeeded", "12 fields from inbox + evidence")
    emit("profile_review", "review_profile", "succeeded", "User confirmed the profile")
    return redirect(url_for("flow.searching"))


@bp.get("/onboarding/searching")
@login_required
def searching():
    s = store()
    if not s.onboarding["profile_saved"]:
        return redirect(url_for("flow.profile_review"))
    return render_template("searching.html", step=2)


@bp.get("/onboarding/benefits")
@login_required
def benefits():
    s = store()
    if not s.onboarding["benefits_ready"]:
        return redirect(url_for("flow.searching"))
    return render_template("benefits.html", step=2, benefits=s.benefits())


@bp.get("/onboarding/benefits/<benefit_id>")
@login_required
def benefit_detail(benefit_id: str):
    s = store()
    benefit = s.benefit(benefit_id)
    if benefit is None:
        return ("Benefit not found", 404)
    s.select_benefit(benefit_id)
    emit("pdf_fetch", "fetch_pdf_form", "succeeded", f"{benefit['form']} from {benefit['agency']}")
    emit("form_fill", "fill_form", "succeeded", f"{len(benefit['form_fields'])} fields")
    return render_template("benefit_detail.html", step=3, benefit=benefit, error=None)


@bp.post("/onboarding/benefits/<benefit_id>/submit")
@login_required
def benefit_submit(benefit_id: str):
    s = store()
    benefit = s.benefit(benefit_id)
    if benefit is None:
        return ("Benefit not found", 404)
    if request.form.get("approve") != "on":
        return render_template("benefit_detail.html", step=3, benefit=benefit,
                               error="Check the approval box before sending.")
    app = s.submit_benefit(benefit_id, actor="user")
    emit("user_approval", "request_approval", "succeeded", "User approved the filled form")
    emit("submit", "mock_submit", "succeeded", app.get("confirmation_id", ""))
    emit("status_check", "poll_status", "succeeded", "Submitted — agency review")
    flash(f"Submitted (mock). Confirmation {app.get('confirmation_id')}.")
    return redirect(url_for("flow.progress", app_id=app["id"]))


@bp.get("/onboarding/benefits/<benefit_id>/pdf")
@login_required
def benefit_pdf(benefit_id: str):
    s = store()
    benefit = s.benefit(benefit_id)
    if benefit is None:
        return ("Benefit not found", 404)
    try:
        path = pdf_fill.build(benefit_id, s)
    except pdf_fill.PdfFillError as exc:
        flash(f"The official PDF could not be filled: {exc}")
        return redirect(url_for("flow.benefit_detail", benefit_id=benefit_id))
    return send_file(path, as_attachment=True, download_name=f"{benefit['form']}-filled.pdf")


@bp.get("/onboarding/progress/<app_id>")
@login_required
def progress(app_id: str):
    s = store()
    app = s.application(app_id)
    if app is None:
        return ("Application not found", 404)
    benefit = s.benefit(app.get("selected_benefit") or s.onboarding.get("selected_benefit") or "")
    return render_template("progress.html", step=3, app=app, benefit=benefit,
                           steps=app.get("progress_steps", []))
