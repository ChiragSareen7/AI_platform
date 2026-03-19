from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings


def log_interaction(
    *,
    question: str,
    response: str,
    sources: List[Dict[str, Any]],
    latency_ms: float,
    model_name: str,
    tokens_in: Optional[int],
    tokens_out: Optional[int],
) -> None:
    """
    Append a single interaction record to a JSONL log file.
    """
    log_path: Path = settings.log_file_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure all values are JSON-serializable (e.g., cast numpy/float32 to Python float)
    safe_sources: List[Dict[str, Any]] = []
    for s in sources:
        s_copy: Dict[str, Any] = dict(s)
        score = s_copy.get("score")
        try:
            if score is not None:
                s_copy["score"] = float(score)
        except (TypeError, ValueError):
            s_copy["score"] = None
        safe_sources.append(s_copy)

    record: Dict[str, Any] = {
        "timestamp": time.time(),
        "question": question,
        "response": response,
        "sources": safe_sources,
        "latency_ms": latency_ms,
        "model_name": model_name,
        "tokens_in": int(tokens_in) if tokens_in is not None else None,
        "tokens_out": int(tokens_out) if tokens_out is not None else None,
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

