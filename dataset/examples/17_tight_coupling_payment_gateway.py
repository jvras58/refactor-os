"""Bad smell: Tight Coupling - esperado: Dependency Injection."""


class SandboxPaymentGateway:
    def authorize(self, card_token: str, amount: float) -> dict:
        if card_token.startswith("blocked"):
            return {"approved": False, "authorization_code": None}
        return {"approved": True, "authorization_code": f"AUTH-{int(amount * 100)}"}

    def capture(self, authorization_code: str) -> dict:
        return {"captured": True, "authorization_code": authorization_code}


class CheckoutService:
    def checkout(self, cart_id: str, card_token: str, items: list[dict]) -> dict:
        gateway = SandboxPaymentGateway()
        amount = sum(item["price"] * item["quantity"] for item in items)
        authorization = gateway.authorize(card_token, amount)
        if not authorization["approved"]:
            return {"cart_id": cart_id, "status": "payment_refused"}

        capture = gateway.capture(authorization["authorization_code"])
        return {
            "cart_id": cart_id,
            "status": "paid" if capture["captured"] else "authorized",
            "amount": round(amount, 2),
        }
