"""Vercel WSGI entrypoint for the MoneyFinder Flask demo."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402

app = create_app()
