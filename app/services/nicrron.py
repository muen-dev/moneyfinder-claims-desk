"""Minimal OpenAI-compatible Nicrron client (server-side only)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..config import Config


class NicrronError(RuntimeError):
    pass


class Nicrron:
    def __init__(self) -> None:
        self.key = Config.NICRRON_API_KEY
        self.base = Config.NICRRON_BASE_URL.rstrip("/")
        self.model = Config.NICRRON_MODEL

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def status(self) -> dict:
        return {
            "name": "Nicrron",
            "status": "configured" if self.enabled else "unavailable",
            "detail": f"{self.model} at {self.base}" if self.enabled else "NICRRON_API_KEY not set",
        }

    def _post(self, path: str, payload: dict, timeout: int = 25) -> dict:
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def complete_json(self, system: str, user: str, model: str | None = None) -> dict:
        """One strict-JSON completion. Retries once. Raises NicrronError on failure."""
        if not self.enabled:
            raise NicrronError("NICRRON_API_KEY is not configured")
        payload = {
            "model": model or self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        last = None
        for _ in range(2):
            try:
                data = self._post("/chat/completions", payload)
                text = data["choices"][0]["message"]["content"]
                return {"data": json.loads(text), "model": data.get("model"), "usage": data.get("usage", {})}
            except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
                last = exc
        raise NicrronError(f"Nicrron call failed: {type(last).__name__}: {last}")

    def ping(self) -> dict:
        if not self.enabled:
            return {"ok": False, "detail": "not configured"}
        try:
            data = self._post(
                "/chat/completions",
                {
                    "model": self.model,
                    "max_tokens": 8,
                    "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
                },
                timeout=15,
            )
            return {"ok": True, "model": data.get("model"), "usage": data.get("usage", {})}
        except Exception as exc:  # noqa: BLE001 - surfaced to the status UI
            return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
