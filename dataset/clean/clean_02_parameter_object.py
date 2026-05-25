"""Código limpo: parâmetros agrupados num dataclass (Parameter Object). Nenhum smell esperado."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InvoiceRequest:
    customer_id: int
    items: list
    discount: float = 0.0
    tax_rate: float = 0.0


def create_invoice(request: InvoiceRequest) -> dict:
    subtotal = sum(item["price"] * item["qty"] for item in request.items)
    total = (subtotal - request.discount) * (1 + request.tax_rate)
    return {"customer": request.customer_id, "total": total}
