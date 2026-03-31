from __future__ import annotations

import os
from contextlib import contextmanager


_TRACEABLE = None


def _load_traceable():
    global _TRACEABLE
    if _TRACEABLE is not None:
        return _TRACEABLE
    try:
        from langsmith import traceable as t  # type: ignore
        _TRACEABLE = t
    except Exception:
        _TRACEABLE = False
    return _TRACEABLE


def traceable_if_enabled(run_type: str, name: str):
    tracing_on = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    traceable = _load_traceable()
    if tracing_on and traceable:
        return traceable(run_type=run_type, name=name)

    def _noop(fn):
        return fn

    return _noop


@contextmanager
def trace_block(name: str):
    # Lightweight manual boundary for code readability.
    yield
