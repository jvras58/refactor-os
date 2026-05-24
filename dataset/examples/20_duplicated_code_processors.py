"""Bad smell: Duplicated Code - esperado: Template Method."""


class OrderProcessor:
    def process(self, payload: dict) -> dict:
        if not payload.get("items"):
            raise ValueError("items are required")
        subtotal = sum(item["price"] * item["quantity"] for item in payload["items"])
        tax = subtotal * 0.08
        total = subtotal + tax
        return {"type": "order", "subtotal": subtotal, "tax": tax, "total": round(total, 2)}


class SubscriptionProcessor:
    def process(self, payload: dict) -> dict:
        if not payload.get("items"):
            raise ValueError("items are required")
        subtotal = sum(item["price"] * item["quantity"] for item in payload["items"])
        discount = subtotal * 0.15 if payload.get("annual_plan") else 0.0
        total = subtotal - discount
        return {"type": "subscription", "subtotal": subtotal, "discount": discount, "total": round(total, 2)}


class RefundProcessor:
    def process(self, payload: dict) -> dict:
        if not payload.get("items"):
            raise ValueError("items are required")
        subtotal = sum(item["price"] * item["quantity"] for item in payload["items"])
        fee = subtotal * 0.03 if payload.get("late_refund") else 0.0
        total = subtotal - fee
        return {"type": "refund", "subtotal": subtotal, "fee": fee, "total": round(total, 2)}
