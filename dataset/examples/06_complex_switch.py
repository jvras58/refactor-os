"""Bad smell: Complex/Long Switch Statements — esperado: Strategy Pattern."""


def process_event(event_type: str, payload: dict) -> dict:
    if event_type == "created":
        if payload.get("priority") == "high":
            return {"status": "queued", "sla": 1}
        elif payload.get("priority") == "low":
            return {"status": "queued", "sla": 24}
        else:
            return {"status": "queued", "sla": 8}
    elif event_type == "updated":
        if payload.get("notify"):
            return {"status": "synced", "notified": True}
        else:
            return {"status": "synced", "notified": False}
    elif event_type == "deleted":
        if payload.get("soft"):
            return {"status": "archived"}
        else:
            return {"status": "purged"}
    elif event_type == "restored":
        if payload.get("verify"):
            return {"status": "active", "verified": True}
        else:
            return {"status": "active", "verified": False}
    elif event_type == "escalated":
        return {"status": "queued", "sla": 1, "escalated": True}
    elif event_type == "merged":
        if payload.get("conflicts"):
            return {"status": "conflict"}
        else:
            return {"status": "merged"}
    elif event_type == "split":
        return {"status": "split", "parts": payload.get("parts", 2)}
    else:
        raise ValueError(f"unknown event: {event_type}")
