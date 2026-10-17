"""MoneyFinder Claims Desk — application factory."""
from __future__ import annotations

from flask import Flask

from .auth import current_user
from .config import Config
from .store import Store
from .services.tracing import Tracing
from .util import money as _money


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    store = Store(root=app.config["ROOT"])
    store.load()
    app.extensions["store"] = store
    app.extensions["tracing"] = Tracing(app)

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
