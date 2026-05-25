"""Solução INCORRETA — defeito: SINTAXE inválida (faltam dois-pontos no método build)."""

from dataclasses import dataclass


@dataclass
class InvoiceData:
    customer_id: int
    items: list
    discount: float
    tax_rate: float

    def build(self) -> dict   # BUG: faltam os dois-pontos -> SyntaxError
        subtotal = sum(item["price"] * item["qty"] for item in self.items)
        total = (subtotal - self.discount) * (1 + self.tax_rate)
        return {"customer": self.customer_id, "total": total}


def create_invoice(customer_id, items, discount, tax_rate) -> dict:
    return InvoiceData(customer_id, items, discount, tax_rate).build()
