"""Run the demo app: python run.py  (or: flask --app app run --debug)."""
from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
