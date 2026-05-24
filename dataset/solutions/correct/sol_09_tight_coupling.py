"""Solução CORRETA — Dependency Injection: conexão injetada (API preservada)."""


class ReportService:
    def __init__(self, conn) -> None:
        # conexão injetada — testes podem passar um banco em memória
        self.conn = conn

    def monthly_totals(self, month: str) -> list[tuple]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT category, SUM(amount) FROM sales WHERE month = ? GROUP BY category", (month,)
        )
        return cursor.fetchall()


def build_report(month: str, conn=None) -> list[tuple]:
    if conn is None:
        import sqlite3

        conn = sqlite3.connect("production.db")
    return ReportService(conn).monthly_totals(month)
