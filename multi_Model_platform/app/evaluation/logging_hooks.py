from __future__ import annotations

from typing import Any, Callable

_hooks: list[Callable[[str, dict[str, Any]], None]] = []


def register_eval_hook(fn: Callable[[str, dict[str, Any]], None]) -> None:
    _hooks.append(fn)


def emit_eval_event(event: str, payload: dict[str, Any]) -> None:
    for fn in _hooks:
        try:
            fn(event, payload)
        except Exception:
            pass
