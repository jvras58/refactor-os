"""Solução CORRETA — Template Method: esqueleto de importação na base, parsing nas subclasses."""

from abc import ABC, abstractmethod


class FileImporter(ABC):
    source = "unknown"

    def import_file(self, path: str) -> dict:
        with open(path) as fh:
            raw = fh.read()
        if not raw.strip():
            raise ValueError("empty file")
        rows = self._parse(raw)
        total = sum(self._amount(r) for r in rows)
        return {"source": self.source, "count": len(rows), "total": total}

    @abstractmethod
    def _parse(self, raw: str) -> list[list[str]]: ...

    @abstractmethod
    def _amount(self, row: list[str]) -> float: ...


class BankImporter(FileImporter):
    source = "bank"

    def _parse(self, raw: str) -> list[list[str]]:
        return [line.split(";") for line in raw.splitlines()]

    def _amount(self, row: list[str]) -> float:
        return float(row[2])


class BrokerImporter(FileImporter):
    source = "broker"

    def _parse(self, raw: str) -> list[list[str]]:
        return [line.split(",") for line in raw.splitlines()]

    def _amount(self, row: list[str]) -> float:
        return float(row[4])
