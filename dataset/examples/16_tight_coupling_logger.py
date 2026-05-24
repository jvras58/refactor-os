"""Bad smell: Tight Coupling - esperado: Dependency Injection."""


class ConsoleAuditLogger:
    def __init__(self):
        self.entries = []

    def info(self, event: str, payload: dict) -> None:
        self.entries.append({"level": "info", "event": event, "payload": payload})

    def warning(self, event: str, payload: dict) -> None:
        self.entries.append({"level": "warning", "event": event, "payload": payload})


class PayrollProcessor:
    def __init__(self):
        self.logger = ConsoleAuditLogger()

    def process_payment(self, employee_id: int, base_salary: float, bonus: float, deductions: float) -> dict:
        gross_amount = base_salary + bonus
        net_amount = gross_amount - deductions
        if net_amount <= 0:
            self.logger.warning("payroll_blocked", {"employee_id": employee_id, "net_amount": net_amount})
            raise ValueError("net amount must be positive")

        payment = {"employee_id": employee_id, "net_amount": round(net_amount, 2)}
        self.logger.info("payroll_processed", payment)
        return payment
