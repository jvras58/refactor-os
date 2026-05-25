"""Código limpo: Template Method já aplicado, sem duplicação. Nenhum smell esperado."""

from abc import ABC, abstractmethod


class ReportGenerator(ABC):
    def generate(self, rows: list[dict]) -> bytes:
        if not rows:
            raise ValueError("empty rows")
        return self._serialize(rows).encode("utf-8")

    @abstractmethod
    def _serialize(self, rows: list[dict]) -> str: ...


class CSVReport(ReportGenerator):
    def _serialize(self, rows: list[dict]) -> str:
        headers = list(rows[0].keys())
        lines = [",".join(headers)]
        lines += [",".join(str(r[h]) for h in headers) for r in rows]
        return "\n".join(lines)
