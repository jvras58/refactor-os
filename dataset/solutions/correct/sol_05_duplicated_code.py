"""Solução CORRETA — Template Method: esqueleto comum na base, variações nas subclasses."""

from abc import ABC, abstractmethod


class ReportGenerator(ABC):
    def generate(self, rows: list[dict]) -> bytes:
        if not rows:
            raise ValueError("empty rows")
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


class HTMLReportGenerator(ReportGenerator):
    def _serialize(self, rows: list[dict]) -> str:
        headers = list(rows[0].keys())
        body = "<table><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
        for row in rows:
            body += "<tr>" + "".join(f"<td>{row[h]}</td>" for h in headers) + "</tr>"
        body += "</table>"
        return body
