"""Código limpo: despacho por dicionário (Strategy já aplicado). Nenhum smell esperado."""

from collections.abc import Callable

_HANDLERS: dict[str, Callable[[float], float]] = {
    "BR": lambda w: 15.0 + w * 2.0,
    "US": lambda w: 10.0 + w * 1.5,
    "DE": lambda w: 12.0 + w * 1.8,
}


def calculate_shipping(country: str, weight_kg: float) -> float:
    handler = _HANDLERS.get(country)
    if handler is None:
        raise ValueError(f"unsupported country: {country}")
    return handler(weight_kg)
