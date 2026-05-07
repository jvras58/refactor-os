"""Bad smell: Long Parameter List — esperado: Builder/Parameter Object."""


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
    subtotal = sum(item["price"] * item["qty"] for item in items)
    total = (subtotal - discount) * (1 + tax_rate)
    return {
        "customer": {"id": customer_id, "name": customer_name, "email": customer_email},
        "billing_address": billing_address,
        "shipping_address": shipping_address,
        "items": items,
        "total": total,
        "currency": currency,
        "due_date": due_date,
    }
