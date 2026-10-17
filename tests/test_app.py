"""Smoke tests: landing/auth, 3-phase onboarding, API contract, money math."""
from __future__ import annotations

import pytest

from app import create_app
from app.services import applications, ledger, packet
from app.services.orchestrator import start_run
from app.services.prism import Prism


@pytest.fixture()
def app():
    application = create_app()
    application.config.update(TESTING=True, DEMO_MODE=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client):
    r = client.post("/signin", data={"email": "marisol@gowanuskettle.example"})
    assert r.status_code == 302
    return r


# ---- landing / auth -------------------------------------------------

def test_landing_is_public(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "MoneyFinder" in html
    assert "Find my benefits" in html


def test_guarded_pages_redirect_to_signin(client):
    for path in ["/dashboard", "/onboarding", "/books", "/run-history", "/settings"]:
        r = client.get(path)
        assert r.status_code == 302, path
        assert "/signin" in r.headers["Location"]


def test_signin_opens_onboarding(client):
    login(client)
    r = client.get("/dashboard")
    assert r.status_code == 200


def test_signin_rejects_bad_email(client):
    r = client.post("/signin", data={"email": "not-an-email"})
    assert r.status_code == 400


# ---- phase 1: consent -> profile ------------------------------------

def test_connect_consent_starts_crawl(client):
    login(client)
    assert client.get("/onboarding/connect").status_code == 200
    r = client.post("/onboarding/connect", follow_redirects=False)
    assert r.status_code == 302 and "/onboarding/crawl" in r.headers["Location"]
    crawl = client.get("/onboarding/crawl")
    assert crawl.status_code == 200
    assert b"Reading your inbox" in crawl.data


def test_profile_requires_crawl_first(client):
    login(client)
    client.post("/onboarding/connect")
    r = client.get("/onboarding/profile")
    assert r.status_code == 302 and "/onboarding/crawl" in r.headers["Location"]


def test_profile_api_and_required_fields(client):
    login(client)
    client.post("/onboarding/connect")
    data = client.get("/api/onboarding/profile").get_json()
    assert len(data["fields"]) == 12
    missing = {f["key"] for f in data["missing_required"]}
    assert missing == set()
    assert all(f["required"] is False for f in data["fields"])


def test_profile_allows_missing_fields_then_goes_to_verification(client, app):
    login(client)
    client.post("/onboarding/connect")
    client.get("/api/onboarding/profile")
    fields = app.extensions["store"].onboarding_fields()
    values = {f"field_{f['key']}": f["value"] for f in fields}
    # leave phone + authorized rep blank: time-boxed demo should still proceed
    r = client.post("/onboarding/profile", data=values)
    assert r.status_code == 302 and "/onboarding/verify" in r.headers["Location"]
    assert app.extensions["store"].onboarding["profile_saved"] is True


def test_verification_stage(client):
    login(client)
    client.post("/onboarding/connect")
    client.get("/api/onboarding/profile")
    s = client.application.extensions["store"]
    values = {f"field_{f['key']}": f["value"] for f in s.onboarding_fields()}
    client.post("/onboarding/profile", data=values)
    page = client.get("/onboarding/verify")
    assert page.status_code == 200
    assert b"Verifying the business" in page.data
    data = client.post("/api/onboarding/verify").get_json()
    assert data["verification"]["verified"] is True
    assert len(data["verification"]["checks"]) == 4
    assert len(data["verification"]["incentives"]) == 2
    # reload shows results
    page = client.get("/onboarding/verify")
    assert b"Verified against government records" in page.data


# ---- phase 2: benefits ---------------------------------------------

def test_benefit_cards_after_search(client):
    login(client)
    client.post("/onboarding/connect")
    s = client.application.extensions["store"]
    values = {f"field_{f['key']}": f["value"] for f in s.onboarding_fields()}
    values["field_phone"] = "(718) 555-0142"
    values["field_authorized_rep"] = "Marisol Vance, Managing Member"
    client.post("/onboarding/profile", data=values)
    client.post("/api/onboarding/verify")
    data = client.get("/api/onboarding/benefits").get_json()
    assert len(data["benefits"]) == 4
    r = client.get("/onboarding/benefits")
    assert r.status_code == 200
    assert b"Why this fits you" in r.data


# ---- phase 3: form -> approval -> progress -------------------------

def _reach_benefits(client):
    login(client)
    client.post("/onboarding/connect")
    client.get("/api/onboarding/profile")
    s = client.application.extensions["store"]
    values = {f"field_{f['key']}": f["value"] for f in s.onboarding_fields()}
    values["field_phone"] = "(718) 555-0142"
    values["field_authorized_rep"] = "Marisol Vance, Managing Member"
    client.post("/onboarding/profile", data=values)
    client.post("/api/onboarding/verify")
    client.get("/api/onboarding/benefits")


def test_form_detail_shows_sourced_fields(client):
    _reach_benefits(client)
    r = client.get("/onboarding/benefits/ben_it636")
    assert r.status_code == 302 and "/filling" in r.headers["Location"]
    client.post("/api/onboarding/benefits/ben_it636/fill")
    r = client.get("/onboarding/benefits/ben_it636")
    assert r.status_code == 200
    assert b"3,104" in r.data
    assert b"Needs your input" in r.data


def test_form_fill_stage_builds_real_pdf(client):
    _reach_benefits(client)
    r = client.get("/onboarding/benefits/ben_it636/filling")
    assert r.status_code == 200
    assert b"Filling your IT-636" in r.data
    r = client.post("/api/onboarding/benefits/ben_it636/fill")
    assert r.status_code == 200
    data = r.get_json()
    assert data["filled"] is True
    assert data["field_count"] >= 8
    assert data["pdf_url"].endswith("/onboarding/benefits/ben_it636/pdf")


def test_submit_requires_approval(client):
    _reach_benefits(client)
    client.post("/api/onboarding/benefits/ben_it636/fill")
    r = client.post("/onboarding/benefits/ben_it636/submit", data={})
    assert r.status_code == 200
    assert b"approval box" in r.data


def test_submit_creates_progress_and_dashboard_entry(client):
    _reach_benefits(client)
    client.post("/api/onboarding/benefits/ben_it636/fill")
    r = client.post("/onboarding/benefits/ben_it636/submit", data={"approve": "on"})
    assert r.status_code == 302 and "/onboarding/progress/" in r.headers["Location"]
    progress = client.get(r.headers["Location"])
    assert progress.status_code == 200
    assert b"Submitted" in progress.data
    app_id = r.headers["Location"].rstrip("/").split("/")[-1]
    desk = client.get("/dashboard")
    assert app_id.encode() in desk.data or b"Claims Desk" in desk.data


# ---- API contract ---------------------------------------------------

def test_api_health_and_profile(client):
    assert client.get("/api/health").get_json()["ok"] is True
    profile = client.get("/api/profile").get_json()
    assert profile["business"]["legal_name"] == "Gowanus Kettle Brewing Co. LLC"
    assert len(profile["facts"]) >= 10
    assert len(profile["conflicts"]) == 3


def test_applications_pipeline(client):
    data = client.get("/api/applications").get_json()
    assert data["count"] == 4
    totals = data["totals"]
    assert totals["identified_cents"] == 4573700
    assert totals["in_process_cents"] == 1507500
    assert totals["approved_cents"] == 746000
    assert totals["paid_cents"] == 0


def test_status_machine_blocks_illegal_transition(client):
    r = client.post("/api/applications/app_it636/transition", json={"to_status": "PAYMENT_CONFIRMED"})
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "invalid_transition"


def test_deposit_requires_payment_issued(app):
    store = app.extensions["store"]
    with pytest.raises(ValueError):
        store.confirm_deposit("app_it643")
    store.transition("app_it212", "PAYMENT_ISSUED")
    app_confirmed = store.confirm_deposit("app_it212")
    assert app_confirmed["status"] == "PAYMENT_CONFIRMED"


def test_ledger_math_excludes_duplicates_and_capital(app):
    store = app.extensions["store"]
    summary = ledger.summary(store.ledger)
    assert summary["transaction_count"] == 39
    assert summary["capital_cents"] == 22800000
    assert summary["missing_receipts"] == 3
    assert summary["reconciled_delta_cents"] == 0


def test_packet_builds_real_files(app):
    store = app.extensions["store"]
    pkt = packet.build(store)
    names = {f["name"] for f in pkt["files"]}
    assert "review-package.md" in names
    assert "ledger.csv" in names
    assert pkt["status"] == "prepared_for_review"


def test_packet_download(client):
    assert client.post("/api/ledger/packet").status_code == 200
    r = client.get("/api/ledger/packet/pkt_2025_demo/ledger.csv")
    assert r.status_code == 200
    assert b"vendor" in r.data


def test_run_has_12_steps_and_human_gate(app):
    store = app.extensions["store"]
    prism = Prism()
    prism.key = ""
    run = start_run(store, prism)
    assert len(run["steps"]) == 12
    assert run["steps"][10]["status"] == "pending"
    assert run["telemetry"] == "pending"
    assert run["prism_url"] is None


def test_demo_reset(client):
    client.post("/api/applications/app_it636/transition", json={"to_status": "FORM_READY"})
    assert client.post("/api/demo/reset").get_json()["ok"] is True
    apps = client.get("/api/applications").get_json()["applications"]
    assert any(a["status"] == "MATCH_FOUND" for a in apps["found"])


def test_filled_official_pdf_downloads(client):
    _reach_benefits(client)
    client.post("/api/onboarding/benefits/ben_it636/fill")
    r = client.get("/onboarding/benefits/ben_it636/pdf")
    assert r.status_code == 200
    assert r.data.startswith(b"%PDF")
    assert len(r.data) > 20_000


def test_progress_requires_submission(client):
    login(client)
    r = client.get("/onboarding/progress/app_it636")
    assert r.status_code == 302 and "/onboarding" in r.headers["Location"]


def test_demo_reset_route_clears_state_and_session(client, app):
    login(client)
    client.post("/onboarding/connect")
    assert app.extensions["store"].onboarding["gmail_connected"] is True
    r = client.get("/demo/reset")
    assert r.status_code == 302 and "/signin" in r.headers["Location"]
    assert app.extensions["store"].onboarding["gmail_connected"] is False
    # session cleared: dashboard should redirect to sign-in
    assert client.get("/dashboard").status_code == 302


def test_profile_building_stage(client):
    login(client)
    client.post("/onboarding/connect")
    r = client.get("/onboarding/profile-building")
    assert r.status_code == 200
    assert b"Building your profile" in r.data
    # crawl -> builder -> profile: API marks the crawl complete
    client.get("/api/onboarding/profile")
    assert client.get("/onboarding/profile").status_code == 200


def test_gov_docs_finder_and_export(client):
    login(client)
    client.get("/api/onboarding/profile")
    s = client.application.extensions["store"]
    values = {f"field_{f['key']}": f["value"] for f in s.onboarding_fields()}
    client.post("/onboarding/profile", data=values)
    client.post("/api/onboarding/verify")
    page = client.get("/gov-docs")
    assert page.status_code == 200
    assert b"Government documents finder" in page.data
    export = client.get("/gov-docs/export").get_json()
    assert len(export["checks"]) == 4
    assert len(export["incentives"]) == 2
    assert export["exported_at"] is not None


def test_signin_page_uses_google_sso(client):
    page = client.get("/signin")
    assert page.status_code == 200
    assert b"Continue with Google" in page.data
    assert b"Welcome back" in page.data


def test_connect_page_has_permission_modal(client):
    login(client)
    page = client.get("/onboarding/connect")
    assert page.status_code == 200
    assert b"Allow MoneyFinder to read your Gmail?" in page.data
    assert b"Allow read-only access" in page.data


def test_signin_resets_onboarding_to_gmail_start(client, app):
    login(client)
    client.post("/onboarding/connect")
    assert app.extensions["store"].onboarding["gmail_connected"] is True
    # a fresh sign-in must start at the Gmail permission modal, not mid-flow
    client.post("/signin", data={"email": "marisol@gowanuskettle.example"})
    assert app.extensions["store"].onboarding["gmail_connected"] is False
    r = client.get("/onboarding")
    assert r.status_code == 302 and "/onboarding/connect" in r.headers["Location"]


def test_observability_endpoint_reports_prism_and_nicrron(client):
    data = client.get("/api/observability").get_json()
    assert data["prism"]["name"] == "PRISM"
    assert data["prism"]["project_id"]
    assert data["prism"]["status"] in {"connected", "unavailable"}
    assert data["nicrron"]["name"] == "Nicrron"
    assert data["nicrron"]["model"]


def test_onboarding_pages_include_observability_card(client):
    login(client)
    page = client.get("/onboarding/connect")
    assert b"Agent observability" in page.data
    assert b"PRISM" in page.data
    assert b"Nicrron" in page.data


def test_crawl_page_lists_documents(client):
    login(client)
    client.post("/onboarding/connect")
    page = client.get("/onboarding/crawl")
    assert page.status_code == 200
    assert b"documents found" in page.data
    assert b"llc-articles.pdf" in page.data


def test_conflict_resolution_endpoint(client, app):
    login(client)
    client.post("/onboarding/connect")
    before = client.application.extensions["store"].onboarding.get("resolved_conflicts", {})
    assert before == {}
    d = client.post("/api/onboarding/conflicts/resolve", json={
        "field": "headcount", "resolution": "Use 14 (year end)",
    }).get_json()
    assert d["remaining"] == 2
    assert app.extensions["store"].onboarding["resolved_conflicts"]["headcount"] == "Use 14 (year end)"
    page = client.get("/onboarding/crawl")
    assert b"2" in page.data
