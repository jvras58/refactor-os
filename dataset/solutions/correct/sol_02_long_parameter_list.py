"""Solução CORRETA — Parameter Object/Builder; assinatura pública preservada por wrapper."""

from dataclasses import dataclass


@dataclass
class InvoiceData:
    customer_id: int
    customer_name: str
    customer_email: str
    billing_address: str
    shipping_address: str
    items: list
    discount: float
    tax_rate: float
    currency: str
    due_date: str

    def build(self) -> dict:
        subtotal = sum(item["price"] * item["qty"] for item in self.items)
        total = (subtotal - self.discount) * (1 + self.tax_rate)
        return {
            "customer": {
                "id": self.customer_id,
                "name": self.customer_name,
                "email": self.customer_email,
            },
            "billing_address": self.billing_address,
            "shipping_address": self.shipping_address,
            "items": self.items,
            "total": total,
            "currency": self.currency,
            "due_date": self.due_date,
        }


def create_invoice(
    customer_id: int,
    customer_name: str,
    customer_email: str,
    billing_address: str,
    shipping_address: str,
    items: list,
    discount: float,
    tax_rate: float,
    currency: str,
    due_date: str,
) -> dict:
    return InvoiceData(
        customer_id,
        customer_name,
        customer_email,
        billing_address,
        shipping_address,
        items,
        discount,
        tax_rate,
        currency,
        due_date,
    ).build()
