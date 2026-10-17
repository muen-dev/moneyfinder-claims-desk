"""Send a PRISM handshake + one real 12-step analysis run (unlocks PRISM onboarding)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.services.orchestrator import start_run
from app.services.prism import Prism

app = create_app()
with app.app_context():
    store = app.extensions["store"]
    prism = Prism()
    print("prism enabled:", prism.enabled)
    handshake = prism.handshake()
    print("handshake:", json.dumps(handshake)[:400])
    run = start_run(store, prism)
    print("run:", run["id"], run["status"], "telemetry:", run["telemetry"],
          "emitted:", prism.emitted, "error:", prism.last_error)
    if prism.last_error:
        sys.exit(1)
