"""MoneyFinder Claims Desk — application factory."""
from __future__ import annotations

import uuid

from flask import Flask, request, session

from .auth import current_user
from .config import Config
from .store import Store
from .services.session_state import SessionState
from .services.tracing import Tracing
from .util import money as _money


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    store = Store(root=app.config["ROOT"])
    store.load()
    app.extensions["store"] = store
    app.extensions["tracing"] = Tracing(app)
    session_state = SessionState()
    app.extensions["session_state"] = session_state

    def _skip_state() -> bool:
        return request.path.startswith("/static/") or request.path == "/api/observability"

    @app.before_request
    def _hydrate_session_state():
        if not session_state.enabled or _skip_state():
            return
        if not session.get("demo_sid"):
            session["demo_sid"] = uuid.uuid4().hex
        state = session_state.load(session["demo_sid"])
        if state:
            store.hydrate_state(state)

    @app.after_request
    def _persist_session_state(response):
        if not session_state.enabled or _skip_state():
            return response
        sid = session.get("demo_sid")
        if sid:
            session_state.save(sid, store.snapshot_state())
        return response

    from .routes.api import bp as api_bp
    from .routes.flow import bp as flow_bp
    from .routes.pages import bp as pages_bp

    app.register_blueprint(flow_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    app.jinja_env.filters["money"] = _money

    def status_label(status: str) -> str:
        return (status or "").replace("_", " ").title()

    app.jinja_env.filters["status_label"] = status_label

    @app.teardown_appcontext
    def _flush_tracing(exc=None):
        tracing = app.extensions.get("tracing")
        if tracing:
            tracing.flush()

    @app.context_processor
    def inject_globals():
        return {
            "banner": "Synthetic demo — not tax advice. Estimates are not money received.",
            "current_user": current_user(),
            "nav": [
                ("/dashboard", "Claims Desk"),
                ("/onboarding", "Onboarding"),
                ("/eligibility", "Eligibility"),
                ("/gov-docs", "Gov Docs"),
                ("/books", "Books"),
                ("/run-history", "Run History"),
                ("/settings", "Settings"),
            ],
        }

    return app
