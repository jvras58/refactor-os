"""Solução INCORRETA — defeito: SINTAXE inválida (faltam dois-pontos no def do handler)."""

from collections.abc import Callable


def _on_created(payload: dict) -> dict
    # BUG: faltam os dois-pontos na assinatura -> SyntaxError
    priority = payload.get("priority")
    if priority == "high":
        return {"status": "queued", "sla": 1}
    return {"status": "queued", "sla": 8}


_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "created": _on_created,
}


def process_event(event_type: str, payload: dict) -> dict:
    handler = _HANDLERS.get(event_type)
    if handler is None:
        raise ValueError(f"unknown event: {event_type}")
    return handler(payload)
