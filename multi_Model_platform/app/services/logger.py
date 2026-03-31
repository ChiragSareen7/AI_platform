from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STORE = Path(__file__).resolve().parents[2] / "store"
LOGS_PATH = STORE / "logs.json"
PERF_PATH = STORE / "model_performance.json"


def ensure_store_files() -> None:
    STORE.mkdir(parents=True, exist_ok=True)
    if not LOGS_PATH.exists():
        LOGS_PATH.write_text("[]")
    if not PERF_PATH.exists():
        PERF_PATH.write_text("{}")


def append_log(entry: dict) -> None:
    ensure_store_files()
    try:
        current = json.loads(LOGS_PATH.read_text())
        if not isinstance(current, list):
            current = []
    except Exception:
        current = []

    current.append({**entry, "timestamp": datetime.now(timezone.utc).isoformat()})
    LOGS_PATH.write_text(json.dumps(current, indent=2))
