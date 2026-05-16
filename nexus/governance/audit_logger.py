from datetime import datetime, timezone


def build_audit_event(event_type: str, payload: dict) -> dict:
    return {
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

