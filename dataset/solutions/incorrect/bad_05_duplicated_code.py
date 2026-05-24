"""Solução INCORRETA — defeito: LÓGICA alterada (validação de 'empty rows' removida)."""

from abc import ABC, abstractmethod


class ReportGenerator(ABC):
    def generate(self, rows: list[dict]) -> bytes:
        # BUG: o original levantava ValueError('empty rows'); essa guarda sumiu.
        return self._serialize(rows).encode("utf-8")

    @abstractmethod
    def _serialize(self, rows: list[dict]) -> str: ...


class CSVReportGenerator(ReportGenerator):
    def _serialize(self, rows: list[dict]) -> str:
        headers = list(rows[0].keys())
        body = ",".join(headers) + "\n"
        for row in rows:
            body += ",".join(str(row[h]) for h in headers) + "\n"
        return body


class JSONReportGenerator(ReportGenerator):
    def _serialize(self, rows: list[dict]) -> str:
        import json

        return json.dumps(rows)
