"""Demo auth: session-based, no password, no OAuth, no real account."""
from __future__ import annotations

from functools import wraps

from flask import redirect, request, session, url_for


def current_user():
    return session.get("user")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("flow.signin", next=request.path))
        return view(*args, **kwargs)

    return wrapped
