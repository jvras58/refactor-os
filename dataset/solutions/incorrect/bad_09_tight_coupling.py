"""Solução INCORRETA — defeito: LÓGICA alterada (consulta SQL perdeu WHERE/GROUP BY)."""


class ReportService:
    def __init__(self, conn) -> None:
        self.conn = conn

    def monthly_totals(self, month: str) -> list[tuple]:
        cursor = self.conn.cursor()
        # BUG: a query original filtrava por month e agrupava por category; isso foi perdido.
        cursor.execute("SELECT category, amount FROM sales")
        return cursor.fetchall()


def build_report(month: str, conn=None) -> list[tuple]:
    if conn is None:
        import sqlite3

        conn = sqlite3.connect("production.db")
    return ReportService(conn).monthly_totals(month)
