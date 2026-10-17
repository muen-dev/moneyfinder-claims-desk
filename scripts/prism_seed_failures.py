"""Seed the PRISM root-cause story: 3 failed v1 runs + 1 passing v2 run.

Run after the live trace smoke test:  .venv/bin/python scripts/prism_seed_failures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.services.prism import Prism  # noqa: E402

app = create_app()
with app.app_context():
    p = Prism()
    for i in range(1, 4):
        ok = p.emit(
            session_id=f"run_fail_00{i}", step="eligibility_extract", tool="extract_eligibility",
            status="failed", latency_ms=820, input_summary="IT-636 official page",
            output_summary="", error="citation missing: eligibility criterion has no verbatim quote",
            version="v1",
        )
        print(f"v1 failed run {i}: delivered={ok} err={p.last_error}")
    p2 = Prism()
    ok = p2.emit(
        session_id="run_v2_001", step="eligibility_extract", tool="extract_eligibility",
        status="ok", latency_ms=540, input_summary="IT-636 official page (v2)",
        output_summary="4 criteria, each with a verbatim quote", version="v2",
    )
    print(f"v2 run: delivered={ok} err={p2.last_error}")
