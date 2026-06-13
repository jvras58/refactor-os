---
title: Strategy — switch de cálculo de taxa por método de pagamento
smell: Complex/Long Switch Statements
pattern: Strategy Pattern
---

# Strategy Pattern — exemplo de solução

Corpus de referência (autoral, distinto do dataset de avaliação). Usado pelo
Recommender via retrieval para guiar a refatoração de **Complex/Long Switch**.

## Problema (antes)

```python
def payment_fee(method: str, amount: float) -> float:
    if method == "pix":
        return 0.0
    elif method == "debit":
        return amount * 0.01
    elif method == "credit":
        return amount * 0.03 + 0.30
    elif method == "boleto":
        return 2.50
    else:
        raise ValueError(f"unknown method: {method}")
```

## Solução (depois)

```python
from collections.abc import Callable

FeeStrategy = Callable[[float], float]

_STRATEGIES: dict[str, FeeStrategy] = {
    "pix": lambda amount: 0.0,
    "debit": lambda amount: amount * 0.01,
    "credit": lambda amount: amount * 0.03 + 0.30,
    "boleto": lambda amount: 2.50,
}


def payment_fee(method: str, amount: float) -> float:
    try:
        strategy = _STRATEGIES[method]
    except KeyError as exc:
        raise ValueError(f"unknown method: {method}") from exc
    return strategy(amount)
```

## Regras aplicadas
- Cada ramo do switch virou uma estratégia isolada.
- O `else` que levantava `ValueError` foi preservado como `KeyError → ValueError`.
- A assinatura pública `payment_fee(method, amount)` não mudou.
