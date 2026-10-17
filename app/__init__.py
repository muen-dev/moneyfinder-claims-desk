"""MoneyFinder Claims Desk — application factory."""
from __future__ import annotations

from flask import Flask

from .config import Config
from .store import Store
from .util import money as _money


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    store = Store(root=app.config["ROOT"])
    store.load()
    app.extensions["store"] = store

    from .routes.pages import bp as pages_bp
    from .routes.api import bp as api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    app.jinja_env.filters["money"] = _money

    def status_label(status: str) -> str:
        return (status or "").replace("_", " ").title()

    app.jinja_env.filters["status_label"] = status_label

    @app.context_processor
    def inject_globals():
        return {
            "banner": "Synthetic demo — not tax advice. Estimates are not money received.",
            "nav": [
                ("/dashboard", "Claims Desk"),
                ("/onboarding", "Onboarding"),
                ("/eligibility", "Eligibility"),
                ("/books", "Books"),
                ("/run-history", "Run History"),
                ("/settings", "Settings"),
            ],
        }

    return app
