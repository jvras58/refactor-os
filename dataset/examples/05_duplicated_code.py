"""Bad smell: Duplicated Code (variações algorítmicas) — esperado: Template Method."""


class CSVReportGenerator:
    def generate(self, rows: list[dict]) -> bytes:
        # passos: coletar -> validar -> serializar -> exportar
        if not rows:
            raise ValueError("empty rows")
        headers = list(rows[0].keys())
        body = ",".join(headers) + "\n"
        for row in rows:
            body += ",".join(str(row[h]) for h in headers) + "\n"
        return body.encode("utf-8")


class JSONReportGenerator:
    def generate(self, rows: list[dict]) -> bytes:
        # mesmo esqueleto: coletar -> validar -> serializar -> exportar
        if not rows:
            raise ValueError("empty rows")
        import json

        body = json.dumps(rows)
        return body.encode("utf-8")


class HTMLReportGenerator:
    def generate(self, rows: list[dict]) -> bytes:
        if not rows:
            raise ValueError("empty rows")
        headers = list(rows[0].keys())
        body = "<table><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
        for row in rows:
            body += "<tr>" + "".join(f"<td>{row[h]}</td>" for h in headers) + "</tr>"
        body += "</table>"
        return body.encode("utf-8")
