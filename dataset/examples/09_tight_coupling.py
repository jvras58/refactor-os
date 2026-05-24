"""Bad smell: Tight Coupling — esperado: Dependency Injection."""

import sqlite3


class ReportService:
    def __init__(self):
        # conexão concreta criada dentro da classe — impossível trocar por um fake nos testes
        self.conn = sqlite3.connect("production.db")

    def monthly_totals(self, month: str) -> list[tuple]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT category, SUM(amount) FROM sales WHERE month = ? GROUP BY category", (month,))
        return cursor.fetchall()


def build_report(month: str) -> list[tuple]:
    service = ReportService()
    return service.monthly_totals(month)
