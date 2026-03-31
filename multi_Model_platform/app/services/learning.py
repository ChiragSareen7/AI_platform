from __future__ import annotations

import json
from pathlib import Path

STORE = Path(__file__).resolve().parents[2] / "store"
PERF_PATH = STORE / "model_performance.json"
LOGS_PATH = STORE / "logs.json"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2))


def get_domain_bias(domain: str) -> str | None:
    perf = _read_json(PERF_PATH, {})
    d = perf.get(domain, {})
    return d.get("best_model")


def update_learning(domain: str, best_model: str, metrics: dict) -> None:
    perf = _read_json(PERF_PATH, {})
    row = perf.get(domain, {"best_model": best_model, "avg_accuracy": 0.0, "avg_latency": 0.0, "count": 0})

    count = int(row.get("count", 0)) + 1
    sem = metrics.get("semantic")
    if isinstance(sem, dict) and not (sem.get("metadata") or {}).get("error"):
        acc_val = float(sem.get("accuracy", metrics["accuracyScore"]))
    else:
        acc_val = metrics["accuracyScore"]
    row["avg_accuracy"] = round(((row.get("avg_accuracy", 0.0) * (count - 1)) + acc_val) / count, 4)
    row["avg_latency"] = round(((row.get("avg_latency", 0.0) * (count - 1)) + metrics["latency"]) / count, 2)
    row["best_model"] = best_model
    row["count"] = count

    perf[domain] = row
    _write_json(PERF_PATH, perf)


def generate_report() -> dict:
    perf = _read_json(PERF_PATH, {})
    logs = _read_json(LOGS_PATH, [])

    total = len(logs)
    avg_latency = 0.0
    if total:
        avg_latency = round(sum(l.get("metrics", {}).get("latency", 0.0) for l in logs) / total, 2)

    return {
        "best_model_per_domain": {k: v.get("best_model") for k, v in perf.items()},
        "average_latency": avg_latency,
        "accuracy_comparison": {k: v.get("avg_accuracy", 0.0) for k, v in perf.items()},
        "total_queries": total,
    }
