"""Vercel WSGI entrypoint for the MoneyFinder Flask demo."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402

flask_app = create_app()


class VercelPathMiddleware:
    """Vercel's catch-all rewrite adds /api/index to PATH_INFO; strip it back off."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"
        if path.startswith("/api/index"):
            path = path[len("/api/index"):] or "/"
            environ["PATH_INFO"] = path
            environ["SCRIPT_NAME"] = ""
        return self.wsgi_app(environ, start_response)


app = VercelPathMiddleware(flask_app)
