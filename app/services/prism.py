"""PRISM emitter. One trace per analysis step; never fakes a successful delivery."""
from __future__ import annotations

import json
import urllib.request

from ..config import Config


class Prism:
    def __init__(self) -> None:
        self.key = Config.PRISMTRACE_API_KEY
        self.project = Config.PRISMTRACE_PROJECT_ID
        self.host = Config.PRISMTRACE_HOST.rstrip("/")
        self._failed = False
        self.last_error: str | None = None
        self.emitted = 0

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.project)

    def status(self) -> dict:
        if not self.enabled:
            return {"name": "PRISM", "status": "unavailable", "detail": "PRISMTRACE_* not set"}
        if self._failed:
            return {"name": "PRISM", "status": "configured", "detail": f"delivery failing: {self.last_error}"}
        return {"name": "PRISM", "status": "configured", "detail": f"project {self.project[:8]}…"}

    def emit(
        self,
        *,
        session_id: str,
        step: str,
        tool: str,
        status: str = "ok",
        latency_ms: int = 0,
        input_summary: str = "",
        output_summary: str = "",
        error: str | None = None,
        version: str = "v1",
    ) -> bool:
        if not self.enabled or self._failed:
            return False
        payload = {
            "project_id": self.project,
            "model": "nicrron/auto",
            "session_id": session_id,
            "agent_id": "moneyfinder-backoffice",
            "input_messages": [{"role": "user", "content": f"[{step}] {input_summary}"[:2000]}],
            "output_message": (error or output_summary or status)[:2000],
            "latency_ms": latency_ms,
            "metadata": {"step": step, "tool": tool, "status": status, "version": version,
                         "synthetic": True},
        }
        req = urllib.request.Request(
            f"{self.host}/api/traces",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-PRISMtrace-Key": self.key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if 200 <= resp.status < 300:
                    self.emitted += 1
                    return True
        except Exception as exc:  # noqa: BLE001 - telemetry must never crash the app
            self.last_error = f"{type(exc).__name__}: {exc}"
            self._failed = True
        return False

    def handshake(self) -> dict:
        if not self.enabled:
            return {"ok": False, "detail": "not configured"}
        req = urllib.request.Request(
            f"{self.host}/api/setup-doctor/handshake",
            data=json.dumps({"project_id": self.project, "send_test_trace": True, "client": "claims-desk"}).encode(),
            headers={"Content-Type": "application/json", "X-PRISMtrace-Key": self.key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
