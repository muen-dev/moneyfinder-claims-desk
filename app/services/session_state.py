"""Persist demo state across Vercel serverless instances (Upstash Redis REST).

Local development has no KV env vars, so this is a no-op. On Vercel, the
project is connected to an Upstash Redis store; each browser session gets a
small JSON state document so the onboarding flow survives instance switches.
"""
from __future__ import annotations

import json
import os
import urllib.request


class SessionState:
    def __init__(self) -> None:
        self.url = (os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
        self.token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
        self.enabled = bool(self.url and self.token)

    def _request(self, path: str, data: bytes | None = None, method: str = "GET") -> bytes | None:
        req = urllib.request.Request(
            f"{self.url}/{path.lstrip('/')}" if path else self.url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.read()

    def load(self, sid: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            raw = self._request(f"get/moneyfinder:state:{sid}")
            payload = json.loads(raw.decode() or "{}")
            result = payload.get("result")
            return json.loads(result) if result else None
        except Exception:  # noqa: BLE001 - state must never break the demo
            return None

    def save(self, sid: str, state: dict) -> None:
        if not self.enabled:
            return
        try:
            body = json.dumps([
                "SET",
                f"moneyfinder:state:{sid}",
                json.dumps(state, separators=(",", ":")),
            ]).encode()
            self._request("", data=body, method="POST")
        except Exception:  # noqa: BLE001
            pass
