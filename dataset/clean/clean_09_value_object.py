"""Código limpo: value object imutável. Nenhum smell esperado."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    amount: int
    currency: str = "BRL"

    def add(self, other: "Money") -> "Money":
        if other.currency != self.currency:
            raise ValueError("currency mismatch")
        return Money(self.amount + other.amount, self.currency)
