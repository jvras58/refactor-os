"""Bad smell: Complex/Long Switch Statements - esperado: Strategy Pattern."""


def calculate_payment_amount(method: str, amount: float, installments: int, customer_score: int) -> dict:
    if method == "credit_card":
        fee = amount * 0.035
        if installments > 1:
            fee += installments * 1.25
        if customer_score < 500:
            fee += amount * 0.02
        status = "manual_review" if amount > 3000 else "approved"
        total = amount + fee
    elif method == "debit_card":
        fee = amount * 0.018
        if customer_score < 400:
            status = "manual_review"
        else:
            status = "approved"
        total = amount + fee
    elif method == "pix":
        fee = 0.0
        discount = amount * 0.03 if amount >= 200 else 0.0
        status = "approved"
        total = amount - discount
    elif method == "boleto":
        fee = 4.50
        if amount > 1500:
            status = "waiting_finance_review"
        else:
            status = "pending_payment"
        total = amount + fee
    elif method == "corporate_invoice":
        fee = 12.0
        if customer_score < 650:
            status = "credit_analysis"
        else:
            status = "invoice_issued"
        total = amount + fee
    else:
        raise ValueError(f"unsupported payment method: {method}")

    return {"method": method, "status": status, "total": round(total, 2)}
