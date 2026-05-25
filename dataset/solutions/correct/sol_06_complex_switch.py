"""Solução CORRETA — Strategy Pattern aplicado ao despacho de eventos (lógica preservada)."""

from collections.abc import Callable


def _on_created(payload: dict) -> dict:
    priority = payload.get("priority")
    if priority == "high":
        return {"status": "queued", "sla": 1}
    if priority == "low":
        return {"status": "queued", "sla": 24}
    return {"status": "queued", "sla": 8}


def _on_updated(payload: dict) -> dict:
    return {"status": "synced", "notified": bool(payload.get("notify"))}


def _on_deleted(payload: dict) -> dict:
    return {"status": "archived"} if payload.get("soft") else {"status": "purged"}


def _on_restored(payload: dict) -> dict:
    return {"status": "active", "verified": bool(payload.get("verify"))}


def _on_merged(payload: dict) -> dict:
    return {"status": "conflict"} if payload.get("conflicts") else {"status": "merged"}


_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "created": _on_created,
    "updated": _on_updated,
    "deleted": _on_deleted,
    "restored": _on_restored,
    "escalated": lambda payload: {"status": "queued", "sla": 1, "escalated": True},
    "merged": _on_merged,
    "split": lambda payload: {"status": "split", "parts": payload.get("parts", 2)},
}


def process_event(event_type: str, payload: dict) -> dict:
    handler = _HANDLERS.get(event_type)
    if handler is None:
        raise ValueError(f"unknown event: {event_type}")
    return handler(payload)
