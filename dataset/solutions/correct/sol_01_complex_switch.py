"""Solução CORRETA — Strategy Pattern aplicado ao switch de frete (lógica preservada)."""

from collections.abc import Callable


def _tiered(light: float, mid: float, heavy: float) -> Callable[[float], float]:
    def calc(weight_kg: float) -> float:
        if weight_kg < 1:
            return light
        if weight_kg < 5:
            return mid
        return heavy

    return calc


_STRATEGIES: dict[str, Callable[[float], float]] = {
    "BR": _tiered(15.0, 35.0, 80.0),
    "US": _tiered(10.0, 25.0, 60.0),
    "DE": _tiered(12.0, 28.0, 70.0),
    "JP": lambda weight_kg: 18.0 + weight_kg * 4.5,
}


def calculate_shipping(country: str, weight_kg: float) -> float:
    strategy = _STRATEGIES.get(country)
    if strategy is None:
        raise ValueError(f"unsupported country: {country}")
    return strategy(weight_kg)
