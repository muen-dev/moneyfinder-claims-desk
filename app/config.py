"""Configuration loaded from environment / .env (no external dependency)."""
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


ROOT = Path(__file__).resolve().parent.parent
_load_dotenv(ROOT / ".env")


class Config:
    ROOT = str(ROOT)
    SECRET_KEY = os.getenv("SECRET_KEY", "claims-desk-demo")
    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes", "on"}

    NICRRON_API_KEY = os.getenv("NICRRON_API_KEY", "")
    NICRRON_BASE_URL = os.getenv("NICRRON_BASE_URL", "https://api.nicrron.ai/v1")
    NICRRON_MODEL = os.getenv("NICRRON_MODEL", "nicrron/auto")

    PRISMTRACE_API_KEY = os.getenv("PRISMTRACE_API_KEY", "")
    PRISMTRACE_PROJECT_ID = os.getenv("PRISMTRACE_PROJECT_ID", "")
    PRISMTRACE_HOST = os.getenv("PRISMTRACE_HOST", "https://api.prism.blockconvey.com")

    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "")
