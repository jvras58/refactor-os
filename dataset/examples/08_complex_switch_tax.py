"""Bad smell: Complex/Long Switch Statements - esperado: Strategy Pattern."""


def calculate_tax(regime: str, gross_revenue: float, payroll: float, has_export_sales: bool) -> dict:
    if regime == "simple_national":
        rate = 0.06
        if gross_revenue > 180000:
            rate = 0.112
        if payroll > gross_revenue * 0.28:
            rate -= 0.01
        deduction = 0.0
    elif regime == "presumed_profit":
        presumed_base = gross_revenue * 0.32
        rate = 0.15
        deduction = 1000.0 if presumed_base > 20000 else 0.0
    elif regime == "real_profit":
        taxable_income = gross_revenue - payroll
        rate = 0.15
        if taxable_income > 50000:
            rate += 0.10
        deduction = payroll * 0.02
    elif regime == "non_profit":
        rate = 0.0
        deduction = 0.0
        if not has_export_sales and gross_revenue > 100000:
            rate = 0.02
    elif regime == "export_company":
        rate = 0.04
        deduction = gross_revenue * 0.01 if has_export_sales else 0.0
    else:
        raise ValueError(f"unsupported tax regime: {regime}")

    taxable_amount = max(gross_revenue - deduction, 0)
    tax_due = taxable_amount * rate
    return {"regime": regime, "rate": rate, "tax_due": round(tax_due, 2)}
