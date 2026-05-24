"""Solução INCORRETA — defeito: PATTERN não aplicado (código segue duplicado)."""


class BankImporter:
    def import_file(self, path: str) -> dict:
        # BUG: alega Template Method, mas o esqueleto continua copiado em cada classe.
        with open(path) as fh:
            raw = fh.read()
        if not raw.strip():
            raise ValueError("empty file")
        rows = [line.split(";") for line in raw.splitlines()]
        total = sum(float(r[2]) for r in rows)
        return {"source": "bank", "count": len(rows), "total": total}


class BrokerImporter:
    def import_file(self, path: str) -> dict:
        with open(path) as fh:
            raw = fh.read()
        if not raw.strip():
            raise ValueError("empty file")
        rows = [line.split(",") for line in raw.splitlines()]
        total = sum(float(r[4]) for r in rows)
        return {"source": "broker", "count": len(rows), "total": total}
