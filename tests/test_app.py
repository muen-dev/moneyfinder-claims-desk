"""Smoke tests: routes, API contract, status machine, ledger and packet."""
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


def test_pages_render(client):
    for path in ["/dashboard", "/onboarding", "/eligibility", "/books", "/run-history", "/settings"]:
        assert client.get(path).status_code == 200, path


def test_onboarding_scan(client):
    r = client.post("/onboarding/scan")
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "What we learned" in html
    assert "Conflicts" in html


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
    assert len(data["applications"]["paid"]) == 0


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
    # duplicate canning line is not double-counted in capital or expenses
    assert summary["capital_cents"] == 18650000 + 4150000
    assert summary["missing_receipts"] == 3
    assert summary["reconciled_delta_cents"] == 0


def test_packet_builds_real_files(app):
    store = app.extensions["store"]
    pkt = packet.build(store)
    names = {f["name"] for f in pkt["files"]}
    assert "review-package.md" in names
    assert "ledger.csv" in names
    assert pkt["status"] == "prepared_for_review"
    for f in pkt["files"]:
        assert f["path"]


def test_packet_download(client):
    assert client.post("/api/ledger/packet").status_code == 200
    r = client.get("/api/ledger/packet/pkt_2025_demo/ledger.csv")
    assert r.status_code == 200
    assert b"vendor" in r.data


def test_run_has_12_steps_and_human_gate(app):
    store = app.extensions["store"]
    prism = Prism()
    prism.key = ""  # do not depend on the network in tests
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


def test_eligibility_has_expired_program(client):
    data = client.get("/api/eligibility").get_json()
    assert data["counts"]["expired"] == 1
    expired = [p for p in data["programs"] if p["verdict"] == "expired"]
    assert expired and expired[0]["id"] == "fed_wotc"
